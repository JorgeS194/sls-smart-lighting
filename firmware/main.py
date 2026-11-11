import time
import config
import logica
import zonas
import controlador
import sensor_pir
import sensor_ldr
import sensor_ultrasonico
import actuador_leds
import historial
import red

# main.py SOLO arma el ciclo principal: lee sensores y le pasa los valores al controlador.
# Dónde vive cada cosa:
#   config.py              -> constantes y números de pin
#   sensor_pir.py          -> PIR + interrupción (hubo_interrupcion(), hay_movimiento())
#   sensor_ultrasonico.py  -> HC-SR04 (medir_cm())
#   sensor_ldr.py          -> LDR (leer())
#   logica.py              -> decisiones (hay_presencia_distancia(), evaluar_zona_*())
#   zonas.py               -> estado de cada zona (zonas.sala, zonas.hab1, zonas.hab2)
#   controlador.py         -> ejecuta los eventos (procesar_presencia(), procesar_ldr())
#   actuador_leds.py       -> 74HC595 (poner(bit, encendido), apagar_todos())
#   historial.py           -> historial de eventos y CSV (registrar_evento())
#   red.py                 -> cola de eventos y WiFi/MQTT en otro hilo
#   mensajes.py            -> contrato JSON de eventos (usado por red.py)

# ==================== INICIO ====================
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
red.iniciar()  # WiFi/MQTT en otro hilo; no espera la conexión para leer sensores

# ==================== CICLO PRINCIPAL ====================
while True:
    # Sala: PIR (por interrupción de hardware + lectura del nivel)
    hubo_irq = sensor_pir.hubo_interrupcion()   # True una sola vez por interrupción
    if hubo_irq:
        print("[SALA] Interrupcion de hardware del PIR (IRQ #{})".format(sensor_pir.contador()))
        historial.registrar_evento("SALA", "IRQ_PIR", sensor_pir.contador())
        red.encolar("SALA", "IRQ_PIR", sensor_pir.contador(), zonas.sala["luz"])
    controlador.procesar_presencia(zonas.sala, hubo_irq or sensor_pir.hay_movimiento())

    # Habitación 1: HC-SR04
    distancia = sensor_ultrasonico.medir_cm()
    hay_alguien = logica.hay_presencia_distancia(distancia)
    controlador.procesar_presencia(zonas.hab1, hay_alguien, int(distancia) if hay_alguien else "")

    # Habitación 2: LDR
    valor_ldr = sensor_ldr.leer()
    controlador.procesar_ldr(zonas.hab2, valor_ldr)

    # Ayuda de calibración (opcional)
    if config.DEPURAR_LDR and time.ticks_diff(time.ticks_ms(), ultimo_debug) >= 1000:
        print("[DEBUG] LDR = {}".format(valor_ldr))
        ultimo_debug = time.ticks_ms()

    time.sleep_ms(config.PAUSA_CICLO_MS)
