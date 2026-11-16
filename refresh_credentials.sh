#!/bin/zsh
# Renueva las credenciales temporales de AWS en .env
# Ejecutar antes de iniciar la app: ./refresh_credentials.sh && reflex run

set -e

SCRIPT_DIR="${0:A:h}"
ENV_FILE="$SCRIPT_DIR/.env"

# Leer variables que no son credenciales
AWS_REGION_VAL=$(grep '^AWS_REGION=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "us-east-1")
LEX_BOT_ID_VAL=$(grep '^LEX_BOT_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")
LEX_BOT_ALIAS_ID_VAL=$(grep '^LEX_BOT_ALIAS_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "")
LEX_LOCALE_ID_VAL=$(grep '^LEX_LOCALE_ID=' "$ENV_FILE" 2>/dev/null | cut -d= -f2 || echo "es_419")

# Exportar credenciales actuales del CLI
eval "$(aws configure export-credentials --format env)"

if [[ -z "$AWS_ACCESS_KEY_ID" ]]; then
  echo "Error: no se pudieron obtener credenciales. Ejecuta 'aws login' primero." >&2
  exit 1
fi

cat > "$ENV_FILE" <<EOF

AWS_REGION=$AWS_REGION_VAL
LEX_BOT_ID=$LEX_BOT_ID_VAL
LEX_BOT_ALIAS_ID=$LEX_BOT_ALIAS_ID_VAL
LEX_LOCALE_ID=$LEX_LOCALE_ID_VAL
# Credenciales temporales — expiran en $AWS_CREDENTIAL_EXPIRATION
AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN=$AWS_SESSION_TOKEN
EOF

echo "Credenciales actualizadas en .env (expiran: $AWS_CREDENTIAL_EXPIRATION)"
