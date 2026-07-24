# LuthorBot Chat

Una interfaz web creada en Python + Reflex para interactuar con LuthorBot, un chatbot creado usando Bedrock, Lex, OpenSearch y S3.
Basada en el código de ejemplo de Reflex, [reflex-chat](https://github.com/reflex-dev/reflex-chat).

## Requisitos previos

- Python >= 3.14
- Cuenta de AWS con permisos sobre Lex, Bedrock, OpenSearch y S3.
- AWS CLI
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes recomendado)
---

## Instalación

```bash
git clone https://github.com/wallsified/reflex-lex-chat.git
cd reflex-lex-chat
uv sync
```

## Configuración

### Variables de entorno

Crear un archivo `.env` en la raíz del proyecto con las siguientes variables:

```bash
AWS_REGION=us-east-1
LEX_BOT_ID=TU_BOT_ID
LEX_BOT_ALIAS_ID=TU_ALIAS_ID
# dependiendo el idioma será el valor. Por ejemplo, español latinoamericano es es_419
LEX_LOCALE_ID=es_419
```

Para esto deberás creado previamente tu bot en la consola de AWS. Puedes seguir los pasos leeyendo
este artículo del [AWS Builder Center](https://builder.aws.com/)

### Credenciales AWS

El boto3 client de Lex V2 utiliza las credenciales estándar de AWS. Asegúrate de que tu entorno tenga configurado:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

con tu cuenta de AWS desde la CLI. Si no la tienes o estás fuera de sesión, usa `aws login` o `aws configure` desde la terminal.

## Ejecutar la aplicación

```bash
reflex init
reflex run
```

La app estará disponible en `http://localhost:3000`.

## Estructura del proyecto

```
reflex-lex-chat/
├── rxconfig.py                    # Configuración de Reflex
├── pyproject.toml                 # Dependencias y metadatos del proyecto
├── .env                           # Variables de entorno (no versionado)
├── chat/
│   ├── __init__.py
│   ├── chat.py                    # Página principal y registro de la app
│   ├── state.py                   # Estado de la aplicación y lógica de Lex V2
│   └── components/
│       ├── __init__.py            # Exportación de componentes
│       ├── chat.py                # Componentes de mensajes y barra de acción
│       └── navbar.py              # Barra de navegación, sidebar y modal
└── assets/                        # Archivos estáticos
```

## Funcionalidades y Notas de Ejecución

- Crear y eliminar sesiones de chat
- Cada sesión mantiene contexto independiente con Amazon Lex V2
- Diseño responsive con tema verde-neón y negro
- Sidebar lateral para navegar entre conversaciones
- Indicador de procesamiento mientras Lex responde
- Manejo de errores con mensajes informativos en el chat
- Las respuestas de Lex pueden contener múltiples mensajes; estos se concatenan en una sola burbuja de respuesta.
- Si la configuración de Lex no está completa o los permisos IAM fallan, se muestra un mensaje de error dentro del chat.