"""Contrato de telemetría compartido por MQTT y la API."""
import json
import math

SENSORES = {"SALA": "PIR", "HABITACION_1": "HC-SR04", "HABITACION_2": "LDR"}
EVENTOS = {"PRESENCIA", "SIN_PRESENCIA", "MUY_CERCA", "OSCURIDAD",
           "OSCURO", "CLARO", "LUZ_SUFICIENTE", "LUZ_ENCENDIDA",
           "LUZ_APAGADA", "ENCENDER_LUZ", "APAGAR_LUZ", "LECTURA", "IRQ_PIR"}
ALIAS_ZONAS = {"HABITACION 1": "HABITACION_1", "HABITACION 2": "HABITACION_2"}
SIN_LECTURA = {"PRESENCIA", "SIN_PRESENCIA", "LUZ_ENCENDIDA", "LUZ_APAGADA",
               "ENCENDER_LUZ", "APAGAR_LUZ"}


def _objeto_json(payload):
    try:
        mensaje = json.loads(payload) if isinstance(payload, (str, bytes)) else payload
    except (ValueError, UnicodeError) as exc:
        raise ValueError("JSON inválido") from exc
    if not isinstance(mensaje, dict):
        raise ValueError("El mensaje debe ser un objeto JSON")
    return mensaje


def validar_mensaje(payload):
    mensaje = _objeto_json(payload)
    zona = mensaje.get("zona")
    if not isinstance(zona, str):
        raise ValueError("Zona inválida")
    zona = ALIAS_ZONAS.get(zona, zona)
    if zona not in SENSORES:
        raise ValueError("Zona inválida")
    sensor = mensaje.get("sensor")
    if sensor != SENSORES[zona]:
        raise ValueError("El sensor no corresponde a la zona")
    valor = mensaje.get("valor")
    evento = mensaje.get("evento", "LECTURA")
    if not isinstance(evento, str) or evento not in EVENTOS:
        raise ValueError("Evento inválido")
    if "luz" in mensaje and type(mensaje["luz"]) is not bool:
        raise ValueError("luz debe ser true o false")
    if "version" in mensaje and (type(mensaje["version"]) is not int or mensaje["version"] != 1):
        raise ValueError("Versión de mensaje no soportada")
    if valor is None or valor == "":
        # Los cambios de luz no siempre tienen una nueva lectura del sensor.
        if evento not in SIN_LECTURA:
            raise ValueError("Este evento requiere una lectura numérica")
        valor = None
    elif evento == "IRQ_PIR":
        # Es un contador de interrupciones, no el nivel binario del PIR.
        if sensor != "PIR" or type(valor) is not int or not 1 <= valor < 2**63:
            raise ValueError("Contador IRQ inválido")
    else:
        if type(valor) not in (int, float) or not -4095 <= valor <= 4095 or not math.isfinite(valor):
            raise ValueError("valor debe ser un número finito dentro del rango del sensor")
        limites = {"PIR": (0, 1), "HC-SR04": (2, 400), "LDR": (0, 4095)}
        minimo, maximo = limites[sensor]
        if not minimo <= valor <= maximo or (sensor in ("PIR", "LDR") and valor != int(valor)):
            raise ValueError("Lectura fuera de rango")
    resultado = dict(zona=zona, sensor=sensor, valor=valor, evento=evento)
    if "luz" in mensaje:
        resultado["luz"] = mensaje["luz"]
    return resultado


def validar_instantanea(payload, dispositivo):
    mensaje = _objeto_json(payload)
    if type(mensaje.get("version")) is not int or mensaje["version"] != 2:
        raise ValueError("Se requiere telemetría v2")
    if not dispositivo or mensaje.get("dispositivo") != dispositivo:
        raise ValueError("El dispositivo no coincide con el tópico")
    sesion = mensaje.get("sesion")
    if not isinstance(sesion, str) or not sesion.strip():
        raise ValueError("Sesión inválida")
    for campo in ("secuencia", "intervalo_ms"):
        valor = mensaje.get(campo)
        if type(valor) is not int or valor <= 0:
            raise ValueError("Campo inválido: " + campo)
    lecturas, luces = mensaje.get("lecturas"), mensaje.get("luces")
    if not isinstance(lecturas, dict) or not isinstance(luces, dict):
        raise ValueError("Se requieren lecturas y luces")
    if any(type(luces.get(zona)) is not bool for zona in SENSORES):
        raise ValueError("Se requiere el estado booleano de las tres luces")
    if any(type(lecturas.get(campo)) is not int for campo in ("pir", "ldr_adc")):
        raise ValueError("PIR y LDR requieren lecturas enteras")
    filas = []
    for zona, campo in (("SALA", "pir"), ("HABITACION_1", "distancia_cm"),
                        ("HABITACION_2", "ldr_adc")):
        dato = dict(zona=zona, sensor=SENSORES[zona], valor=lecturas.get(campo),
                    evento="LECTURA", luz=luces[zona])
        if campo == "distancia_cm" and dato["valor"] is None:
            # Registrar el estado observado sin sustituir la última distancia.
            dato["evento"] = "LUZ_ENCENDIDA" if dato["luz"] else "LUZ_APAGADA"
        filas.append(validar_mensaje(dato))
    return filas


def validar_comando(mensaje):
    if not isinstance(mensaje, dict):
        raise ValueError("El comando debe ser un objeto")
    zona, accion = mensaje.get("zona"), mensaje.get("accion")
    if not isinstance(zona, str) or zona not in SENSORES:
        raise ValueError("Zona inválida")
    if accion not in ("encender", "apagar", "auto"):
        raise ValueError("accion debe ser encender, apagar o auto")
    return {"zona": zona, "accion": accion}
