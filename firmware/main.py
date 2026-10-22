import time
import config
import sensor_pir
import sensor_ldr
import sensor_ultrasonico
import actuador_leds
# >>> INICIO CSV (descomentar SOLO en un ESP32 real; Wokwi no lo necesita)
# import os
# <<< FIN CSV

# ==================== PINES (los números vienen de config.py) ====================
# Sala: el PIR y su interrupción se configuran dentro de sensor_pir.py
# Habitación 1: el HC-SR04 se configura dentro de sensor_ultrasonico.py
# Habitación 2: el LDR se configura dentro de sensor_ldr.py
# LEDs: el 74HC595 (DS, STCP, SHCP) se configura dentro de actuador_leds.py

# ==================== INTERRUPCIÓN DE HARDWARE (PIR) ====================
# (la ISR y su bandera viven en sensor_pir.py -> hubo_interrupcion())

# ==================== HISTORIAL Y CSV ====================
historial = []   # lista en RAM: (tiempo_ms, zona, evento, valor)

def registrar_evento(zona, evento, valor=""):
    """Guarda el evento en el historial. La escritura al CSV está comentada."""
    ahora = time.ticks_ms()
    historial.append((ahora, zona, evento, valor))
    if len(historial) > config.MAX_HISTORIAL:
        historial.pop(0)
    # >>> INICIO CSV (descomentar SOLO en un ESP32 real)
    # try:
    #     nuevo = config.ARCHIVO_CSV not in os.listdir()
    #     with open(config.ARCHIVO_CSV, "a") as f:
    #         if nuevo:
    #             f.write("tiempo_ms,zona,evento,valor\n")
    #         f.write("{},{},{},{}\n".format(ahora, zona, evento, valor))
    # except OSError as e:
    #     print("[CSV] No se pudo escribir:", e)
    # <<< FIN CSV

def exportar_csv():
    """Imprime el CSV por el puerto serie para copiarlo (llamar desde la REPL)."""
    # >>> INICIO CSV (descomentar SOLO en un ESP32 real)
    # try:
    #     with open(config.ARCHIVO_CSV) as f:
    #         print(f.read())
    # except OSError:
    #     print("[CSV] Aun no existe", config.ARCHIVO_CSV)
    # <<< FIN CSV
    pass

# ==================== CONTROL DE LOS LEDs ====================
# (el 74HC595 vive en actuador_leds.py -> poner(bit, encendido), apagar_todos())

# ==================== LECTURA DE SENSORES ====================
# (el PIR vive en sensor_pir.py -> hubo_interrupcion(), hay_movimiento())
# (la medición del HC-SR04 vive en sensor_ultrasonico.py -> medir_cm())
# (la lectura del LDR vive en sensor_ldr.py -> leer())

# ==================== ESTADO DE CADA ZONA ====================
sala = {"nombre": "SALA", "bit": config.BIT_SALA,
        "presencia": False, "luz": False, "ultima": 0}
hab1 = {"nombre": "HABITACION 1", "bit": config.BIT_HAB1,
        "presencia": False, "luz": False, "ultima": 0}
hab2 = {"nombre": "HABITACION 2", "bit": config.BIT_HAB2,
        "oscuro": False, "luz": False}

# ==================== LÓGICA DE LAS ZONAS ====================
def controlar_zona_presencia(z, hay_presencia, detalle=""):
    """Sala y Habitación 1: enciende con presencia y apaga tras TIEMPO_APAGADO."""
    ahora = time.ticks_ms()

    # Mensajes solo cuando cambia el estado del sensor
    if hay_presencia and not z["presencia"]:
        print("[{}] Presencia detectada{}".format(z["nombre"], detalle))
        registrar_evento(z["nombre"], "PRESENCIA", detalle.strip(" ()"))
    elif not hay_presencia and z["presencia"]:
        print("[{}] Sin presencia".format(z["nombre"]))
        registrar_evento(z["nombre"], "SIN_PRESENCIA")
    z["presencia"] = hay_presencia

    if hay_presencia:
        z["ultima"] = ahora   # reinicia el contador de apagado
        if not z["luz"]:
            actuador_leds.poner(z["bit"], True)
            z["luz"] = True
            print("[{}] Luz ENCENDIDA".format(z["nombre"]))
            registrar_evento(z["nombre"], "LUZ_ENCENDIDA")
    elif z["luz"]:
        if time.ticks_diff(ahora, z["ultima"]) >= config.TIEMPO_APAGADO * 1000:
            actuador_leds.poner(z["bit"], False)
            z["luz"] = False
            print("[{}] Luz APAGADA".format(z["nombre"]))
            registrar_evento(z["nombre"], "LUZ_APAGADA")

def controlar_zona_ldr(z, valor):
    """Habitación 2: enciende con poca luz y apaga con luz suficiente."""
    # Con histéresis: el umbral cambia según el estado actual
    if config.OSCURO_ES_VALOR_ALTO:
        if z["oscuro"]:
            oscuro = valor > config.UMBRAL_LUZ - config.HISTERESIS_LUZ
        else:
            oscuro = valor > config.UMBRAL_LUZ + config.HISTERESIS_LUZ
    else:
        if z["oscuro"]:
            oscuro = valor < config.UMBRAL_LUZ + config.HISTERESIS_LUZ
        else:
            oscuro = valor < config.UMBRAL_LUZ - config.HISTERESIS_LUZ

    if oscuro and not z["oscuro"]:
        print("[{}] Oscuridad detectada (LDR = {})".format(z["nombre"], valor))
        registrar_evento(z["nombre"], "OSCURIDAD", valor)
        actuador_leds.poner(z["bit"], True)
        z["luz"] = True
        print("[{}] Luz ENCENDIDA".format(z["nombre"]))
        registrar_evento(z["nombre"], "LUZ_ENCENDIDA")
    elif not oscuro and z["oscuro"]:
        print("[{}] Luz ambiente suficiente (LDR = {})".format(z["nombre"], valor))
        registrar_evento(z["nombre"], "LUZ_SUFICIENTE", valor)
        actuador_leds.poner(z["bit"], False)
        z["luz"] = False
        print("[{}] Luz APAGADA".format(z["nombre"]))
        registrar_evento(z["nombre"], "LUZ_APAGADA")
    z["oscuro"] = oscuro

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
        registrar_evento("SALA", "IRQ_PIR", sensor_pir.contador())
    controlar_zona_presencia(sala, hubo_irq or sensor_pir.hay_movimiento())

    # Habitación 1: HC-SR04
    distancia = sensor_ultrasonico.medir_cm()
    hay_alguien = distancia is not None and distancia < config.DISTANCIA_PRESENCIA
    detalle = " (a {} cm)".format(int(distancia)) if hay_alguien else ""
    controlar_zona_presencia(hab1, hay_alguien, detalle)

    # Habitación 2: LDR
    valor_ldr = sensor_ldr.leer()
    controlar_zona_ldr(hab2, valor_ldr)

    # Ayuda de calibración (opcional)
    if config.DEPURAR_LDR and time.ticks_diff(time.ticks_ms(), ultimo_debug) >= 1000:
        print("[DEBUG] LDR = {}".format(valor_ldr))
        ultimo_debug = time.ticks_ms()

    time.sleep_ms(config.PAUSA_CICLO_MS)