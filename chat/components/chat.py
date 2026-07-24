"""Componentes del área de mensajes y barra de acción.

Define los componentes responsables de renderizar los mensajes
de la conversación (preguntas del usuario y respuestas de Lex)
y la barra de entrada para enviar nuevas preguntas.
"""

import reflex as rx

from chat.state import QA, State
from reflex.constants.colors import ColorType


def message_content(text: str, color: ColorType) -> rx.Component:
    """Crea un componente de contenido de mensaje con formato Markdown.

    Renderiza el texto proporcionado como Markdown con un color de fondo
    y texto personalizados, dentro de un contenedor con bordes redondeados.

    Args:
        text: Texto a mostrar en el mensaje. Se renderiza como Markdown.
        color: Identificador del color del tema de Reflex a utilizar
            para el fondo y el texto del mensaje.

    Returns:
        rx.Component: Componente Markdown con el estilo aplicado.
    """
    return rx.markdown(
        text,
        background_color=rx.color(color, 4),
        color=rx.color(color, 12),
        display="inline-block",
        padding_inline="1em",
        border_radius="8px",
        border="1px solid #00ff4133",
    )


def message(qa: QA) -> rx.Component:
    """Renderiza un par de pregunta y respuesta como un mensaje del chat.

    La pregunta se alinea a la derecha con color verde, y la respuesta
    se alinea a la izquierda con el mismo esquema de color verde.

    Args:
        qa: Diccionario con las claves "question" y "answer" que
            representan el intercambio del usuario y el bot.

    Returns:
        rx.Component: Contenedor con ambas burbujas de mensaje.
    """
    return rx.box(
        rx.box(
            message_content(qa["question"], "grass"),
            text_align="right",
            margin_bottom="8px",
        ),
        rx.box(
            message_content(qa["answer"], "grass"),
            text_align="left",
            margin_bottom="8px",
        ),
        max_width="50em",
        margin_inline="auto",
    )


def chat() -> rx.Component:
    """Renderiza el área de mensajes con auto-scroll.

    Muestra todos los mensajes de la sesión de chat activa usando
    un contenedor con auto-scroll que se desplaza automáticamente
    al último mensaje cuando se agrega nuevo contenido.

    Returns:
        rx.Component: Componente auto_scroll con la lista de mensajes.
    """
    return rx.auto_scroll(
        rx.foreach(State.selected_chat, message),
        flex="1",
        padding="10px",
    )


def action_bar() -> rx.Component:
    """Renderiza la barra de acción para enviar mensajes.

    Contiene un formulario con un campo de texto y un botón de envío,
    un mensaje de advertencia sobre las respuestas de Lex, y el logo
    de la aplicación. La barra se fija en la parte inferior de la
    pantalla con efecto de desenfoque en el fondo.

    Returns:
        rx.Component: Barra de acción sticky con formulario y controles.
    """
    return rx.center(
        rx.vstack(
            rx.form(
                rx.hstack(
                    rx.input(
                        rx.input.slot(),
                        placeholder="Escribe un mensaje para LuthorBot.",
                        id="question",
                        flex="1",
                    ),
                    rx.button(
                        "Enviar Pregunta",
                        loading=State.processing,
                        disabled=State.processing,
                        type="submit",
                    ),
                    max_width="50em",
                    margin="0 auto",
                    align_items="center",
                ),
                reset_on_submit=True,
                on_submit=State.process_question,
            ),
            rx.text(
                "LuthorBot puede devolver respuestas incorrectas o incompletas.",
                text_align="center",
                font_size=".75em",
                color="#00ff4199",
            ),
            width="100%",
            padding_x="16px",
            align="stretch",
        ),
        position="sticky",
        bottom="0",
        left="0",
        padding_y="16px",
        backdrop_filter="auto",
        backdrop_blur="lg",
        border_top="1px solid #00ff4133",
        background_color="#111111",
        align="stretch",
        width="100%",
    )
