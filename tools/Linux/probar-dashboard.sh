#!/usr/bin/env bash
# Equivalente en bash de probar-dashboard.cmd (PR #38).
# Uso:  ./probar-dashboard.sh [nombre-del-dispositivo]
# El nombre debe ser IGUAL al MQTT_DISPOSITIVO de tu copia de Wokwi.
set -euo pipefail

# Ir a la raíz del repo (donde está este archivo), igual que "pushd %~dp0".
cd "$(dirname "${BASH_SOURCE[0]}")"

DISPOSITIVO="${1:-${SLS_DISPOSITIVO:-demo-sala-jorge}}"
PUERTO="${SLS_PUERTO:-8018}"
URL="http://127.0.0.1:${PUERTO}/"

# Activar el entorno virtual si existe (se crea una sola vez).
if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

# Comprobar que paho-mqtt está instalado (igual que el chequeo del .cmd).
if ! python -c "import paho.mqtt.client" 2>/dev/null; then
    echo "Faltan dependencias. Crea el entorno una sola vez con:"
    echo "  python3 -m venv .venv && source .venv/bin/activate"
    echo "  python -m pip install -r backend/requirements.txt"
    exit 1
fi

echo "Dashboard:   ${URL}"
echo "Dispositivo: ${DISPOSITIVO}  (debe coincidir con MQTT_DISPOSITIVO en Wokwi)"
echo "Ctrl+C para detener."

# Abrir el navegador 2 s después de arrancar (si hay xdg-open).
( sleep 2; xdg-open "${URL}" >/dev/null 2>&1 || true ) &

# "exec" reemplaza este script por el backend: Ctrl+C lo detiene limpio.
exec python -u -m backend.main \
    --broker broker.emqx.io \
    --prefijo utp/ds8/1gs133/sls-smart-lighting \
    --puerto "${PUERTO}" \
    --dispositivo-comandos "${DISPOSITIVO}"
