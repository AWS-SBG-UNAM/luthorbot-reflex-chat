"""Estado de la aplicación y lógica de integración con Amazon Lex V2.

Este módulo define el estado global de la aplicación de chat,
incluyendo la gestión de múltiples sesiones de conversación,
el procesamiento de preguntas a través de Amazon Lex V2 y
el manejo de errores de la API.
"""

import os
import re

import boto3
import reflex as rx
from botocore.exceptions import BotoCoreError, ClientError
from typing import Any, TypedDict


def _sanitize_session_id(name: str) -> str:
    """Convierte un nombre de chat en un sessionId válido para Amazon Lex V2.

    Reemplaza cualquier carácter que no sea alfanumérico, punto, guión bajo,
    dos puntos o guión por un guión, y garantiza que el resultado no esté vacío.

    Args:
        name: Nombre del chat tal como lo escribió el usuario.

    Returns:
        String que cumple el patrón [0-9a-zA-Z._:-]+.
    """
    safe = re.sub(r"[^0-9a-zA-Z._:-]", "-", name)
    return safe or "chat"


class QA(TypedDict):
    """Representa un par de pregunta y respuesta en el chat.

    Attributes:
        question: La pregunta formulada por el usuario.
        answer: La respuesta generada por Amazon Lex V2.
    """

    question: str
    answer: str


def _lex_settings() -> tuple[str, str, str, str]:
    """Carga y valida la configuración de Amazon Lex desde variables de entorno.

    Lee las siguientes variables de entorno:
    - `AWS_REGION`: Región de AWS donde está desplegado el bot.
    - `LEX_BOT_ID`: Identificador del bot de Lex V2.
    - `LEX_BOT_ALIAS_ID`: Identificador del alias del bot.
    - `LEX_LOCALE_ID`: Identificador del idioma (opcional, por defecto "en_US").

    Returns:
        Tupla con (region, bot_id, bot_alias_id, locale_id).

    Raises:
        ValueError: Si falta alguna variable de entorno obligatoria
            (AWS_REGION, LEX_BOT_ID o LEX_BOT_ALIAS_ID).
    """
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
            "Falta configuración para inicializar Lex. ¿Ya recargaste el .env?\n. Falta:"
            + ", ".join(missing)
        )

    return region, bot_id, bot_alias_id, locale_id


class State(rx.State):
    """Estado principal de la aplicación de chat.

    Gestiona las sesiones de chat, la navegación entre conversaciones
    y la comunicación con Amazon Lex. Cada sesión de chat se identifica
    por un nombre único que se usa como sessionId en Lex para preservar
    el contexto conversacional.

    Attributes:
        _chats: Diccionario interno que almacena todas las sesiones de chat.
            Cada clave es el nombre de la sesión y el valor es una lista
            de pares QA (pregunta y respuesta).
        current_chat: Nombre de la sesión de chat actualmente activa.
        processing: Indica si se está procesando una respuesta de Lex.
        is_modal_open: Controla la visibilidad del modal de creación de chat.
    """

    _chats: dict[str, list[QA]] = {
        "Nuevo Chat con LuthorBot": [],
    }

    current_chat = "Nuevo Chat con LuthorBot"
    processing: bool = False
    is_modal_open: bool = False
    new_chat_name: str = ""

    @rx.event
    def create_chat(self, form_data: dict[str, Any]):
        """Crea una nueva sesión de chat con el nombre proporcionado.

        Extrae el nombre del nuevo chat del formulario, lo agrega al
        diccionario de chats, establece la sesión actual y cierra el modal.

        Args:
            form_data: Diccionario con los datos del formulario. Debe
                contener la clave "new_chat_name" con el nombre deseado.
        """
        new_chat_name = self.new_chat_name.strip()
        if not new_chat_name:
            return
        self.current_chat = new_chat_name
        self._chats[new_chat_name] = []
        self.is_modal_open = False
        self.new_chat_name = ""

    @rx.event
    def set_is_modal_open(self, is_open: bool):
        """Actualiza el estado de visibilidad del modal de creación de chat.

        Args:
            is_open: `True` para abrir el modal, `False` para cerrarlo.
        """
        self.is_modal_open = is_open

    @rx.var
    def selected_chat(self) -> list[QA]:
        """Retorna la lista de mensajes de la sesión de chat activa.

        Returns:
            Lista de pares QA de la sesión actual. Retorna una lista
            vacía si la sesión actual no existe en el diccionario.
        """
        return (
            self._chats[self.current_chat] if self.current_chat in self._chats else []
        )

    @rx.event
    def delete_chat(self, chat_name: str):
        """Elimina una sesión de chat por su nombre.

        Si se elimina la sesión activa, se cambia a la primera sesión
        disponible. Si no quedan sesiones, se recrea la sesión por
        defecto "Nuevo Chat".

        Args:
            chat_name: Nombre de la sesión a eliminar.
        """
        if chat_name not in self._chats:
            return
        del self._chats[chat_name]
        if len(self._chats) == 0:
            self._chats = {"Nuevo-Chat": []}
        if self.current_chat not in self._chats:
            self.current_chat = list(self._chats.keys())[0]

    @rx.event
    def set_chat(self, chat_name: str):
        """Cambia la sesión de chat activa.

        Args:
            chat_name: Nombre de la sesión a la que se desea cambiar.
        """
        self.current_chat = chat_name

    @rx.event
    def set_new_chat_name(self, new_chat_name: str):
        """Actualiza el nombre para un nuevo chat (utilizado por formularios).

        Args:
            new_chat_name: Nombre propuesto para el nuevo chat.
        """
        self.new_chat_name = new_chat_name

    @rx.var
    def chat_titles(self) -> list[str]:
        """Retorna los nombres de todas las sesiones de chat disponibles.

        Returns:
            Lista de strings con los nombres de las sesiones de chat.
        """
        return list(self._chats.keys())

    @rx.event
    async def process_question(self, form_data: dict[str, Any]):
        """Procesa una pregunta recibida del formulario de entrada.

        Extrae la pregunta del formulario y delega el procesamiento
        al método `lex_process_question`. No procesa preguntas vacías.

        Args:
            form_data: Diccionario con los datos del formulario. Debe
                contener la clave "question" con el texto de la pregunta.
        """
        question = form_data["question"]
        if not question:
            return

        async for value in self.lex_process_question(question):
            yield value

    @rx.event
    async def lex_process_question(self, question: str):
        """Envía una pregunta a Amazon Lex V2 y procesa la respuesta.

        Este método realiza los siguientes pasos:
        1. Agrega la pregunta al historial de la sesión actual.
        2. Establece el estado `processing` en `True`.
        3. Carga la configuración de Lex V2.
        4. Envía la pregunta al bot usando `recognize_text`.
        5. Extrae y concatena los mensajes de respuesta.
        6. Actualiza la respuesta en el historial de chat.
        7. En caso de error, muestra un mensaje descriptivo en el chat.

        Args:
            question: Texto de la pregunta del usuario.
        """
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
                "\n".join(contents).strip()
                or "Lo siento amo Luthor, no puedo responder esa pregunta."
            )
            self._chats[self.current_chat][-1]["answer"] = answer
        except (ValueError, BotoCoreError, ClientError) as err:
            self._chats[self.current_chat][-1]["answer"] = (
                f"Error de Lex: {err}. Revisa variables de entorno y permisos de IAM de tu cuenta."
            )
        finally:
            self._chats = self._chats
            self.processing = False
            yield
