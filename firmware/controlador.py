# controlador.py: une las DECISIONES con las ACCIONES.
#   logica.py decide (qué pasó: PRESENCIA, LUZ_ENCENDIDA, etc.) y devuelve una lista de eventos.
#   controlador.py ejecuta cada evento: LED, mensaje en consola e historial.
# Este archivo NO lee sensores y NO conoce pines: recibe la zona y los valores ya medidos.
# Cualquier efecto nuevo de un evento (por ejemplo, publicarlo por MQTT en la Etapa 3)
# se agrega en aplicar_evento(), para que todos los eventos pasen por un solo lugar.

import time
import logica
import actuador_leds
import historial
import red


def aplicar_evento(zona, evento, dato=""):
    """Ejecuta un evento que decidió logica.py: LED, mensaje y historial.
    'dato' es la distancia (Habitación 1) o el valor del LDR (Habitación 2)."""
    nombre = zona["nombre"]

    if evento == "PRESENCIA":
        detalle = "a {} cm".format(dato) if dato != "" else ""
        mostrado = " ({})".format(detalle) if detalle else ""
        print("[{}] Presencia detectada{}".format(nombre, mostrado))
        historial.registrar_evento(nombre, "PRESENCIA", detalle)
    elif evento == "SIN_PRESENCIA":
        print("[{}] Sin presencia".format(nombre))
        historial.registrar_evento(nombre, "SIN_PRESENCIA")
    elif evento == "OSCURIDAD":
        print("[{}] Oscuridad detectada (LDR = {})".format(nombre, dato))
        historial.registrar_evento(nombre, "OSCURIDAD", dato)
    elif evento == "LUZ_SUFICIENTE":
        print("[{}] Luz ambiente suficiente (LDR = {})".format(nombre, dato))
        historial.registrar_evento(nombre, "LUZ_SUFICIENTE", dato)
    elif evento == "LUZ_ENCENDIDA":
        actuador_leds.poner(zona["bit"], True)
        print("[{}] Luz ENCENDIDA".format(nombre))
        historial.registrar_evento(nombre, "LUZ_ENCENDIDA")
    elif evento == "LUZ_APAGADA":
        actuador_leds.poner(zona["bit"], False)
        print("[{}] Luz APAGADA".format(nombre))
        historial.registrar_evento(nombre, "LUZ_APAGADA")

    # Enviar el dato numérico original sin cambiar consola ni historial local.
    red.encolar(nombre, evento, dato, zona["luz"])


def procesar_presencia(zona, hay_presencia, dato=""):
    """Sala y Habitación 1: logica.py decide, controlador.py ejecuta."""
    for evento in logica.evaluar_zona_presencia(zona, hay_presencia, time.ticks_ms()):
        aplicar_evento(zona, evento, dato)


def procesar_ldr(zona, valor):
    """Habitación 2: logica.py decide, controlador.py ejecuta."""
    for evento in logica.evaluar_zona_ldr(zona, valor):
        aplicar_evento(zona, evento, valor)
