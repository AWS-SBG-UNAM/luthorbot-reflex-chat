"""Componentes de navegación: barra superior, sidebar y modal.

Define los componentes de navegación de la aplicación, incluyendo
la barra superior con indicador de sesión activa, el sidebar
lateral con la lista de sesiones y el modal para crear nuevas
conversaciones.
"""

import reflex as rx

from chat.state import State


def sidebar_chat(chat: str) -> rx.Component:
    """Renderiza un elemento individual en el sidebar de chats.

    Cada elemento contiene un botón con el nombre de la sesión
    (que al hacer clic cambia a esa sesión) y un botón de eliminar
    con icono de papelera en color rojo.

    Args:
        chat: Nombre de la sesión de chat a renderizar.

    Returns:
        rx.Component: Elemento del drawer con los botones de
            selección y eliminación de la sesión.
    """
    return rx.drawer.close(
        rx.hstack(
            rx.button(
                chat,
                on_click=lambda: State.set_chat(chat),
                width="80%",
                variant="surface",
            ),
            rx.button(
                rx.icon(
                    tag="trash",
                    on_click=State.delete_chat(chat),
                    stroke_width=1,
                ),
                width="20%",
                variant="surface",
                color_scheme="red",
            ),
            width="100%",
        ),
        key=chat,
    )


def sidebar(trigger) -> rx.Component:
    """Renderiza el sidebar lateral con la lista de sesiones de chat.

    El sidebar se despliega desde la izquierda y contiene un encabezado
    "LuthorBot", un divisor y la lista de todas las sesiones de chat
    disponibles generadas dinámicamente.

    Args:
        trigger: Componente que activa la apertura del sidebar
            (generalmente un botón con icono).

    Returns:
        rx.Component: Drawer lateral con la lista de sesiones.
    """
    return rx.drawer.root(
        rx.drawer.trigger(trigger),
        rx.drawer.overlay(),
        rx.drawer.portal(
            rx.drawer.content(
                rx.vstack(
                    rx.heading("Tus chats con LuthorBot", color="#00ff41", as_="h2"),
                    rx.divider(),
                    rx.foreach(State.chat_titles, lambda chat: sidebar_chat(chat)),
                    align_items="stretch",
                    width="100%",
                ),
                top="auto",
                right="auto",
                height="100%",
                width="20em",
                padding="2em",
                background_color="#111111",
                outline="none",
            )
        ),
        direction="left",
    )


def modal(trigger) -> rx.Component:
    """Renderiza el modal para crear una nueva sesión de chat.

    El modal contiene un formulario con un campo de texto para
    ingresar el nombre del nuevo chat y un botón para confirmar
    la creación. Se abre y cierra mediante el estado `is_modal_open`.

    Args:
        trigger: Componente que activa la apertura del modal
            (generalmente un botón con icono de "+" ).

    Returns:
        rx.Component: Diálogo modal con el formulario de creación.
    """
    return rx.dialog.root(
        rx.dialog.trigger(trigger),
        rx.dialog.content(
            rx.form(
                rx.hstack(
                    rx.input(
                        placeholder="Nombre del chat",
                        value=State.new_chat_name,
                        on_change=State.set_new_chat_name,
                        flex="1",
                        min_width="20ch",
                    ),
                    rx.button("Crear chat"),
                    spacing="2",
                    wrap="wrap",
                    width="100%",
                ),
                on_submit=State.create_chat,
            ),
            background_color="#0a0a0a",
        ),
        open=State.is_modal_open,
        on_open_change=State.set_is_modal_open,
    )


def navbar() -> rx.Component:
    """Renderiza la barra de navegación superior.

    Contiene tres elementos principales:
    - Un badge con el nombre de la sesión de chat activa.
    - Un botón para abrir el modal de creación de nuevo chat.
    - Un botón para abrir el sidebar con la lista de sesiones.

    Returns:
        rx.Component: Barra de navegación horizontal con los
            controles de sesión y navegación.
    """
    return rx.hstack(
        rx.badge(
            State.current_chat,
            rx.tooltip(
                rx.icon("info", size=14),
                content="Sesión activa.",
            ),
            size="3",
            variant="soft",
            color_scheme="green",
            margin_inline_end="auto",
        ),
        modal(
            rx.icon_button("message-square-plus"),
        ),
        sidebar(
            rx.icon_button(
                "messages-square",
                background_color="#00ff4133",
            )
        ),
        justify_content="space-between",
        align_items="center",
        padding="12px",
        border_bottom="1px solid #00ff4133",
        background_color="#111111",
    )
