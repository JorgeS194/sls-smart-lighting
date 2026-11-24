#!/usr/bin/env bash
# Menú para mandar órdenes a las 3 luces SIN usar el navegador ni mosquitto.
# Habla con el backend (que ya debe estar corriendo con probar-dashboard.sh)
# y el backend las publica por MQTT al ESP32 de Wokwi.
# Uso:  ./probar-ordenes.sh
set -uo pipefail

API="http://127.0.0.1:${SLS_PUERTO:-8018}"

enviar() {   # $1 = zona, $2 = acción
    curl -s -w '\n  -> HTTP %{http_code}\n' -X POST "${API}/api/comandos" \
        -H 'Content-Type: application/json' \
        -d "{\"zona\":\"$1\",\"accion\":\"$2\"}"
}

estado() {   # muestra luz, modo y última orden confirmada por la placa
    curl -s "${API}/api/estado" | python3 -c '
import json, sys
datos = json.load(sys.stdin)
for zona, d in datos["zonas"].items():
    print("  {:13} luz={!s:5} modo={:6} orden_confirmada={}".format(
        zona, d["luz"], d["modo"], d["orden_id"]))
'
}

while true; do
    cat <<'MENU'

 [1] SALA encender         [2] SALA apagar          [3] SALA auto
 [4] HABITACION_1 encender [5] HABITACION_1 apagar  [6] HABITACION_1 auto
 [7] HABITACION_2 encender [8] HABITACION_2 apagar  [9] HABITACION_2 auto
 [i] Orden inválida (debe dar 400)   [e] Ver estado   [s] Salir
MENU
    read -r -p "Opción: " op
    case "$op" in
        1) enviar SALA encender ;;
        2) enviar SALA apagar ;;
        3) enviar SALA auto ;;
        4) enviar HABITACION_1 encender ;;
        5) enviar HABITACION_1 apagar ;;
        6) enviar HABITACION_1 auto ;;
        7) enviar HABITACION_2 encender ;;
        8) enviar HABITACION_2 apagar ;;
        9) enviar HABITACION_2 auto ;;
        i) enviar COCINA encender ;;
        e) estado ;;
        s) exit 0 ;;
        *) echo "Opción no válida" ;;
    esac
done
