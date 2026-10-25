import time
import config
import logica
import zonas
import sensor_pir
import sensor_ldr
import sensor_ultrasonico
import actuador_leds
import historial

# ==================== PINES (los números vienen de config.py) ====================
# Sala: el PIR y su interrupción se configuran dentro de sensor_pir.py
# Habitación 1: el HC-SR04 se configura dentro de sensor_ultrasonico.py
# Habitación 2: el LDR se configura dentro de sensor_ldr.py
# LEDs: el 74HC595 (DS, STCP, SHCP) se configura dentro de actuador_leds.py

# ==================== LECTURA DE SENSORES ====================
# (el PIR vive en sensor_pir.py -> hubo_interrupcion(), hay_movimiento())
# (la medición del HC-SR04 vive en sensor_ultrasonico.py -> medir_cm())
# (la lectura del LDR vive en sensor_ldr.py -> leer())

# ==================== DECISIONES ====================
# (la lógica vive en logica.py -> hay_presencia_distancia(), esta_oscuro(),
#  evaluar_zona_presencia(), evaluar_zona_ldr())

# ==================== ACTUADORES Y REGISTRO ====================
# (el 74HC595 vive en actuador_leds.py -> poner(bit, encendido), apagar_todos())
# (el historial y el CSV viven en historial.py -> registrar_evento())

# ==================== ESTADO DE CADA ZONA ====================
# (el estado de sala, hab1 y hab2 vive en zonas.py -> zonas.sala, zonas.hab1, zonas.hab2)

# ==================== EJECUTAR LAS DECISIONES ====================
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


def procesar_presencia(zona, hay_presencia, dato=""):
    """Sala y Habitación 1: logica.py decide, main.py ejecuta."""
    for evento in logica.evaluar_zona_presencia(zona, hay_presencia, time.ticks_ms()):
        aplicar_evento(zona, evento, dato)


def procesar_ldr(zona, valor):
    """Habitación 2: logica.py decide, main.py ejecuta."""
    for evento in logica.evaluar_zona_ldr(zona, valor):
        aplicar_evento(zona, evento, valor)

# ==================== PROGRAMA PRINCIPAL ====================
actuador_leds.apagar_todos()   # todos los LEDs apagados al iniciar

print("=================================")
print(" CASA INTELIGENTE - ESP32")
print("=================================")
print("Sistema iniciado correctamente")
print("Lectura inicial del LDR: {} (UMBRAL_LUZ = {})\n".format(sensor_ldr.leer(), config.UMBRAL_LUZ))

ultimo_debug = time.ticks_ms()

# Calentamiento del HC-SR04: se descarta la primera medición y se espera
# a que termine cualquier eco pendiente (el sensor necesita ~60 ms entre mediciones).
sensor_ultrasonico.medir_cm()
time.sleep_ms(60)

while True:
    # Sala: PIR (por interrupción de hardware + lectura del nivel)
    hubo_irq = sensor_pir.hubo_interrupcion()   # True una sola vez por interrupción
    if hubo_irq:
        print("[SALA] Interrupcion de hardware del PIR (IRQ #{})".format(sensor_pir.contador()))
        historial.registrar_evento("SALA", "IRQ_PIR", sensor_pir.contador())
    procesar_presencia(zonas.sala, hubo_irq or sensor_pir.hay_movimiento())

    # Habitación 1: HC-SR04
    distancia = sensor_ultrasonico.medir_cm()
    hay_alguien = logica.hay_presencia_distancia(distancia)
    procesar_presencia(zonas.hab1, hay_alguien, int(distancia) if hay_alguien else "")

    # Habitación 2: LDR
    valor_ldr = sensor_ldr.leer()
    procesar_ldr(zonas.hab2, valor_ldr)

    # Ayuda de calibración (opcional)
    if config.DEPURAR_LDR and time.ticks_diff(time.ticks_ms(), ultimo_debug) >= 1000:
        print("[DEBUG] LDR = {}".format(valor_ldr))
        ultimo_debug = time.ticks_ms()

    time.sleep_ms(config.PAUSA_CICLO_MS)