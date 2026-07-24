"""Configuración de la aplicación Reflex.

Define la configuración global de la aplicación Reflex,
incluyendo el nombre del módulo raíz, los plugins activos
y las opciones de telemetría.
"""

import reflex as rx

config = rx.Config(
    app_name="chat",
    api_url="http://52.71.52.190:8000",
    plugins=[rx.plugins.SitemapPlugin()],
    show_built_with_reflex=False,
    telemetry_enabled=False,
    # Como no ocuparemos mucha configuración de interfaz, inyectamos la configuración
    # de tailwind de manera directa.
    tailwind={
        "theme": {
            "extend": {
                "colors": {
                    "neon": "#00ff41",
                    "dark": {
                        "900": "#0a0a0a",
                        "800": "#111111",
                        "700": "#1a1a1a",
                        "600": "#222222",
                    },
                },
            },
        },
    },
)
