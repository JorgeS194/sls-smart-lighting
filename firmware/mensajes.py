"""Contrato JSON v1; sin hardware, red ni escritura de archivos."""
import json
import config

SENSORES = {"SALA": "PIR", "HABITACION 1": "HC-SR04", "HABITACION 2": "LDR"}


def evento(zona, nombre, valor, luz, secuencia, sesion, tiempo_ms):
    """valor conserva su tipo: distancia/LDR/IRQ numéricos o texto vacío."""
    return json.dumps({
        "version": 1, "dispositivo": config.MQTT_DISPOSITIVO,
        "sesion": sesion, "secuencia": secuencia, "tiempo_ms": tiempo_ms,
        "zona": zona, "sensor": SENSORES[zona], "evento": nombre,
        "valor": valor, "luz": luz,
    }).encode("utf-8")


def telemetria(sesion, secuencia, pir, ldr, distancia, luces):
    if distancia is not None and not 2 <= distancia <= 400:
        distancia = None
    return json.dumps({
        "version": 2, "dispositivo": config.MQTT_DISPOSITIVO,
        "sesion": sesion, "secuencia": secuencia,
        "intervalo_ms": config.TELEMETRIA_INTERVALO_MS,
        "lecturas": {"pir": int(pir), "ldr_adc": ldr, "distancia_cm": distancia},
        "luces": luces,
    }).encode("utf-8")


def estado(sesion, disponibilidad):
    return json.dumps({
        "version": 2, "dispositivo": config.MQTT_DISPOSITIVO,
        "sesion": sesion, "estado": disponibilidad,
    }).encode("utf-8")


def latido(sesion, descartados, tiempo_ms):
    return json.dumps({
        "version": 1, "dispositivo": config.MQTT_DISPOSITIVO,
        "sesion": sesion, "tiempo_ms": tiempo_ms,
        "evento": "LATIDO", "descartados": descartados,
    }).encode("utf-8")
