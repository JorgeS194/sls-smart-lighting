# logica.py: las DECISIONES del sistema (cuándo hay presencia, cuándo está oscuro,
# cuándo se enciende o se apaga una luz).
# Este archivo NO toca hardware, NO imprime y NO guarda historial: solo recibe
# valores, decide y devuelve qué pasó. Ejecutar esas decisiones (LEDs, print,
# historial) es responsabilidad de main.py.

import time
import config


# ==================== CLASIFICACIÓN DE LECTURAS ====================
def hay_presencia_distancia(distancia):
    """Habitación 1: True si el HC-SR04 midió algo más cerca que DISTANCIA_PRESENCIA."""
    return distancia is not None and distancia < config.DISTANCIA_PRESENCIA


def esta_oscuro(valor, estaba_oscuro):
    """Habitación 2: clasifica la lectura del LDR con histéresis.
    El umbral cambia según el estado actual para evitar parpadeos cerca del límite."""
    if config.OSCURO_ES_VALOR_ALTO:
        if estaba_oscuro:
            return valor > config.UMBRAL_LUZ - config.HISTERESIS_LUZ
        return valor > config.UMBRAL_LUZ + config.HISTERESIS_LUZ
    if estaba_oscuro:
        return valor < config.UMBRAL_LUZ + config.HISTERESIS_LUZ
    return valor < config.UMBRAL_LUZ - config.HISTERESIS_LUZ


# ==================== DECISIÓN POR ZONA ====================
# Cada función actualiza el estado de la zona (el diccionario z) y devuelve una
# lista con los EVENTOS que ocurrieron en esta vuelta (puede estar vacía).

def evaluar_zona_presencia(z, hay_presencia, ahora):
    """Sala y Habitación 1: enciende con presencia y apaga tras TIEMPO_APAGADO.
    Eventos posibles: PRESENCIA, SIN_PRESENCIA, LUZ_ENCENDIDA, LUZ_APAGADA."""
    eventos = []

    # Evento solo cuando cambia el estado del sensor
    if hay_presencia and not z["presencia"]:
        eventos.append("PRESENCIA")
    elif not hay_presencia and z["presencia"]:
        eventos.append("SIN_PRESENCIA")
    z["presencia"] = hay_presencia

    if hay_presencia:
        z["ultima"] = ahora   # reinicia el contador de apagado
        if not z["luz"]:
            z["luz"] = True
            eventos.append("LUZ_ENCENDIDA")
    elif z["luz"]:
        if time.ticks_diff(ahora, z["ultima"]) >= config.TIEMPO_APAGADO * 1000:
            z["luz"] = False
            eventos.append("LUZ_APAGADA")

    return eventos


def evaluar_zona_ldr(z, valor):
    """Habitación 2: enciende con poca luz y apaga con luz suficiente.
    Eventos posibles: OSCURIDAD, LUZ_ENCENDIDA, LUZ_SUFICIENTE, LUZ_APAGADA."""
    eventos = []
    oscuro = esta_oscuro(valor, z["oscuro"])

    if oscuro and not z["oscuro"]:
        z["luz"] = True
        eventos.append("OSCURIDAD")
        eventos.append("LUZ_ENCENDIDA")
    elif not oscuro and z["oscuro"]:
        z["luz"] = False
        eventos.append("LUZ_SUFICIENTE")
        eventos.append("LUZ_APAGADA")

    z["oscuro"] = oscuro
    return eventos