import asyncio
import base64
import gzip
import json
import os
import re
import subprocess

import boto3
import reflex as rx
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, TypedDict


def _sanitize_session_id(name: str) -> str:
    safe = re.sub(r"[^0-9a-zA-Z._:-]", "-", name)
    return safe or "chat"


class QA(TypedDict):
    question: str
    answer: str


def _lex_settings() -> tuple[str, str, str, str]:
    region = os.getenv("AWS_REGION", "")
    bot_id = os.getenv("LEX_BOT_ID", "")
    bot_alias_id = os.getenv("LEX_BOT_ALIAS_ID", "")
    locale_id = os.getenv("LEX_LOCALE_ID", "en_US")
    missing = []
    if not region:
        missing.append("AWS_REGION")
    if not bot_id:
        missing.append("LEX_BOT_ID")
    if not bot_alias_id:
        missing.append("LEX_BOT_ALIAS_ID")
    if missing:
        raise ValueError(
            "Falta configuracion para inicializar Lex. Falta: " + ", ".join(missing)
        )
    return region, bot_id, bot_alias_id, locale_id


def _webm_to_pcm(data: bytes) -> bytes:
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-i",
                "pipe:0",
                "-f",
                "s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "pipe:1",
            ],
            input=data,
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("ffmpeg excedio el tiempo limite de 30 segundos.")
    except FileNotFoundError:
        raise RuntimeError("ffmpeg no esta disponible en este servidor.")
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg fallo (codigo {proc.returncode}).")
    return proc.stdout


def _decode_lex_field(value: str) -> str:
    if not value:
        return ""
    try:
        return gzip.decompress(base64.b64decode(value)).decode("utf-8")
    except Exception:
        return value


class _TranscriptCollector(TranscriptResultStreamHandler):
    """Acumula los resultados finales del stream de Transcribe."""

    def __init__(self, stream):
        super().__init__(stream)
        self._parts: list[str] = []

    async def handle_transcript_event(self, event: TranscriptEvent):
        for result in event.transcript.results:
            if not result.is_partial:
                for alt in result.alternatives:
                    self._parts.append(alt.transcript)

    @property
    def transcript(self) -> str:
        return " ".join(self._parts).strip()


async def _transcribe_pcm(pcm: bytes, region: str, language_code: str = "es-US") -> str:
    """Transcribe raw PCM (16 kHz, 16-bit, mono) usando Transcribe Streaming."""
    client = TranscribeStreamingClient(region=region)
    stream = await client.start_stream_transcription(
        language_code=language_code,
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )

    async def _feed():
        chunk_size = 3200  # 100 ms a 16 kHz 16-bit mono
        for i in range(0, len(pcm), chunk_size):
            await stream.input_stream.send_audio_event(
                audio_chunk=pcm[i : i + chunk_size]
            )
        await stream.input_stream.end_stream()

    collector = _TranscriptCollector(stream.output_stream)
    await asyncio.gather(_feed(), collector.handle_events())
    return collector.transcript


def _polly_speak(text: str, region: str, language_code: str = "es-US") -> str:
    """Sintetiza texto con Polly y devuelve el audio como base64 MP3."""
    # Lupe es la voz neural en español latinoamericano
    client = boto3.client("polly", region_name=region)
    response = client.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Lupe",
        LanguageCode=language_code,
        Engine="neural",
    )
    audio_bytes = response["AudioStream"].read()
    return base64.b64encode(audio_bytes).decode()


_START_JS = (
    "navigator.mediaDevices.getUserMedia({audio: true})"
    ".then(stream => {"
    "  window._luthor_rec = new MediaRecorder(stream);"
    "  window._luthor_chunks = [];"
    "  window._luthor_rec.ondataavailable = e => window._luthor_chunks.push(e.data);"
    "  window._luthor_rec.start();"
    "  setTimeout(() => {"
    "    if (window._luthor_rec && window._luthor_rec.state === 'recording') {"
    "      window._luthor_rec.stop();"
    "    }"
    "  }, 120000);"
    "})"
    ".catch(err => { window._luthorMicError(err.name); });"
)

_STOP_JS = (
    "new Promise(resolve => {"
    "  const r = window._luthor_rec;"
    "  r.onstop = async () => {"
    "    r.stream.getTracks().forEach(t => t.stop());"
    "    const blob = new Blob(window._luthor_chunks, {type: r.mimeType});"
    "    const bytes = new Uint8Array(await blob.arrayBuffer());"
    "    let bin = '';"
    "    for (let i = 0; i < bytes.length; i += 0x8000)"
    "      bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));"
    "    resolve(btoa(bin));"
    "  };"
    "  r.stop();"
    "})"
)


class State(rx.State):
    _chats: dict[str, list[QA]] = {"Nuevo Chat con LuthorBot": []}
    current_chat = "Nuevo Chat con LuthorBot"
    processing: bool = False
    is_modal_open: bool = False
    new_chat_name: str = ""
    recording: bool = False

    @rx.event
    def create_chat(self, form_data: dict[str, Any]):
        new_chat_name = self.new_chat_name.strip()
        if not new_chat_name:
            return
        self.current_chat = new_chat_name
        self._chats[new_chat_name] = []
        self.is_modal_open = False
        self.new_chat_name = ""

    @rx.event
    def set_is_modal_open(self, is_open: bool):
        self.is_modal_open = is_open

    @rx.var
    def selected_chat(self) -> list[QA]:
        return (
            self._chats[self.current_chat] if self.current_chat in self._chats else []
        )

    @rx.event
    def delete_chat(self, chat_name: str):
        if chat_name not in self._chats:
            return
        del self._chats[chat_name]
        if len(self._chats) == 0:
            self._chats = {"Nuevo-Chat": []}
        if self.current_chat not in self._chats:
            self.current_chat = list(self._chats.keys())[0]

    @rx.event
    def set_chat(self, chat_name: str):
        self.current_chat = chat_name

    @rx.event
    def set_new_chat_name(self, new_chat_name: str):
        self.new_chat_name = new_chat_name

    @rx.var
    def chat_titles(self) -> list[str]:
        return list(self._chats.keys())

    @rx.event
    async def process_question(self, form_data: dict[str, Any]):
        question = form_data["question"]
        if not question:
            return
        async for value in self.lex_process_question(question):
            yield value

    @rx.event
    async def lex_process_question(self, question: str):
        qa = QA(question=question, answer="")
        self._chats[self.current_chat].append(qa)
        self.processing = True
        yield
        try:
            region, bot_id, bot_alias_id, locale_id = _lex_settings()
            client = boto3.client("lexv2-runtime", region_name=region)
            response = client.recognize_text(
                botId=bot_id,
                botAliasId=bot_alias_id,
                localeId=locale_id,
                sessionId=_sanitize_session_id(self.current_chat),
                text=question,
            )
            messages = response.get("messages", [])
            contents = [m.get("content", "") for m in messages if m.get("content")]
            answer = (
                "".join(contents).strip()
                or "Lo siento amo Luthor, no puedo responder esa pregunta."
            )
            self._chats[self.current_chat][-1]["answer"] = answer
        except (ValueError, BotoCoreError, ClientError) as err:
            self._chats[self.current_chat][-1]["answer"] = (
                f"Error de Lex: {err}. Revisa variables de entorno y permisos de IAM."
            )
        finally:
            self._chats = self._chats
            self.processing = False
            yield

    @rx.event
    def start_recording(self):
        if self.processing:
            return
        self.recording = True
        return rx.call_script(_START_JS)

    @rx.event
    def stop_recording(self):
        self.recording = False
        return rx.call_script(_STOP_JS, callback=State.process_audio)

    @rx.event
    def handle_mic_error(self, error_name: str):
        self.recording = False
        if error_name in ("NotAllowedError", "PermissionDeniedError"):
            msg = "Micrófono denegado. Permite el acceso en la configuración del navegador."
        elif error_name in ("NotFoundError", "DevicesNotFoundError"):
            msg = "No se encontró un micrófono disponible."
        else:
            msg = f"Grabación de voz no disponible en este navegador ({error_name})."
        qa = QA(question="", answer=msg)
        self._chats[self.current_chat].append(qa)
        self._chats = self._chats

    @rx.event
    async def process_audio(self, audio_b64: str):
        raw = base64.b64decode(audio_b64)
        if not raw:
            qa = QA(question="", answer="No se capturo audio.")
            self._chats[self.current_chat].append(qa)
            self._chats = self._chats
            self.processing = False
            return
        self.processing = True
        yield

        # 1. WebM → PCM
        try:
            pcm = _webm_to_pcm(raw)
        except RuntimeError as err:
            qa = QA(question="", answer=f"Error de conversión de audio: {err}")
            self._chats[self.current_chat].append(qa)
            self._chats = self._chats
            self.processing = False
            return

        # 2. PCM → texto via Transcribe Streaming
        try:
            region, bot_id, bot_alias_id, locale_id = _lex_settings()
            transcript = await _transcribe_pcm(pcm, region, language_code="es-US")
        except Exception as err:
            qa = QA(question="", answer=f"Error de Transcribe: {err}")
            self._chats[self.current_chat].append(qa)
            self._chats = self._chats
            self.processing = False
            return

        if not transcript:
            qa = QA(question="", answer="No se entendió el audio. Intenta de nuevo.")
            self._chats[self.current_chat].append(qa)
            self._chats = self._chats
            self.processing = False
            return

        # 3. Texto → Lex
        try:
            lex_client = boto3.client("lexv2-runtime", region_name=region)
            lex_response = lex_client.recognize_text(
                botId=bot_id,
                botAliasId=bot_alias_id,
                localeId=locale_id,
                sessionId=_sanitize_session_id(self.current_chat),
                text=transcript,
            )
            messages = lex_response.get("messages", [])
            contents = [m.get("content", "") for m in messages if m.get("content")]
            answer = (
                "".join(contents).strip()
                or "Lo siento amo Luthor, no puedo responder esa pregunta."
            )
        except (BotoCoreError, ClientError, ValueError) as err:
            qa = QA(question=transcript, answer=f"Error de Lex: {err}")
            self._chats[self.current_chat].append(qa)
            self._chats = self._chats
            self.processing = False
            return

        qa = QA(question=transcript, answer=answer)
        self._chats[self.current_chat].append(qa)
        self._chats = self._chats
        self.processing = False
        yield

        # 4. Respuesta → voz via Polly
        try:
            mp3_b64 = _polly_speak(answer, region, language_code="es-US")
            yield rx.call_script(
                f"new Audio('data:audio/mpeg;base64,{mp3_b64}').play().catch(()=>{{}})"
            )
        except BotoCoreError, ClientError:
            # Polly es opcional: si falla, la respuesta de texto ya está visible
            pass
