"""Contrato de telemetría compartido por MQTT y la API."""
import json
import math

SENSORES = {"SALA": "PIR", "HABITACION_1": "HC-SR04", "HABITACION_2": "LDR"}
EVENTOS = {"PRESENCIA", "SIN_PRESENCIA", "MUY_CERCA", "OSCURIDAD",
           "OSCURO", "CLARO", "LUZ_SUFICIENTE", "LUZ_ENCENDIDA",
           "LUZ_APAGADA", "ENCENDER_LUZ", "APAGAR_LUZ", "LECTURA", "IRQ_PIR"}


def validar_mensaje(payload):
    try:
        mensaje = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    except (ValueError, UnicodeError) as exc:
        raise ValueError("JSON inválido") from exc
    if not isinstance(mensaje, dict):
        raise ValueError("El mensaje debe ser un objeto JSON")
    zona = mensaje.get("zona")
    if not isinstance(zona, str) or zona not in SENSORES:
        raise ValueError("Zona inválida")
    sensor = mensaje.get("sensor")
    if sensor != SENSORES[zona]:
        raise ValueError("El sensor no corresponde a la zona")
    valor = mensaje.get("valor")
    if type(valor) not in (int, float) or not math.isfinite(valor):
        raise ValueError("valor debe ser un número finito")
    limites = {"PIR": (0, 1), "HC-SR04": (2, 400), "LDR": (0, 4095)}
    minimo, maximo = limites[sensor]
    if not minimo <= valor <= maximo or (sensor in ("PIR", "LDR") and valor != int(valor)):
        raise ValueError("Lectura fuera de rango")
    evento = mensaje.get("evento", "LECTURA")
    if not isinstance(evento, str) or evento not in EVENTOS:
        raise ValueError("Evento inválido")
    if "luz" in mensaje and type(mensaje["luz"]) is not bool:
        raise ValueError("luz debe ser true o false")
    resultado = dict(zona=zona, sensor=sensor, valor=valor, evento=evento)
    if "luz" in mensaje:
        resultado["luz"] = mensaje["luz"]
    return resultado


def validar_comando(mensaje):
    if not isinstance(mensaje, dict):
        raise ValueError("El comando debe ser un objeto")
    zona, accion = mensaje.get("zona"), mensaje.get("accion")
    if not isinstance(zona, str) or zona not in SENSORES:
        raise ValueError("Zona inválida")
    if accion not in ("encender", "apagar", "auto"):
        raise ValueError("accion debe ser encender, apagar o auto")
    return {"zona": zona, "accion": accion}
