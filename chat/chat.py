"""Página principal de la aplicación de chat.

Define la función `index()` que compone la interfaz completa
de la aplicación combinando la barra de navegación, el área
de mensajes y la barra de acción. También inicializa la
aplicación Reflex con el tema configurado.
"""

import reflex as rx

from chat.components import chat, navbar


def index() -> rx.Component:
    """Construye y retorna la página principal de la aplicación.

    Combina tres componentes principales en un layout vertical:
    - La barra de navegación (navbar) en la parte superior.
    - El área de mensajes del chat en el centro.
    - La barra de acción para enviar mensajes en la parte inferior.

    Returns:
        rx.Component: Componente raíz de la página con diseño vertical
            que ocupa el 100% de la altura de la ventana del navegador.
    """
    return rx.vstack(
        navbar(),
        chat.chat(),
        chat.action_bar(),
        background_color="#0a0a0a",
        color="#e0e0e0",
        height="100dvh",
        align_items="stretch",
        spacing="0",
    )


app = rx.App(
    theme=rx.theme(
        appearance="dark",
        accent_color="green",
    ),
)
app.add_page(index)
