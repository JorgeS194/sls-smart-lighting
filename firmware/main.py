from machine import Pin, time_pulse_us
import time
import config
import sensor_ldr
# >>> INICIO CSV (descomentar SOLO en un ESP32 real; Wokwi no lo necesita)
# import os
# <<< FIN CSV

# ==================== PINES (los números vienen de config.py) ====================
pir = Pin(config.PIN_PIR, Pin.IN)            # Sala: salida del PIR
trig = Pin(config.PIN_TRIG, Pin.OUT)         # Habitación 1: TRIG del HC-SR04
echo = Pin(config.PIN_ECHO, Pin.IN)          # Habitación 1: ECHO del HC-SR04
# Habitación 2: el LDR ahora se configura dentro de sensor_ldr.py

ds = Pin(config.PIN_DS, Pin.OUT)             # 74HC595: DS   (datos)
stcp = Pin(config.PIN_STCP, Pin.OUT)         # 74HC595: STCP (latch)
shcp = Pin(config.PIN_SHCP, Pin.OUT)         # 74HC595: SHCP (reloj)

# ==================== INTERRUPCIÓN DE HARDWARE (PIR) ====================
# El PIR avisa por interrupción (flanco de subida en GPIO13). La rutina de
# interrupción (ISR) solo levanta una bandera: es corta y no imprime ni usa
# memoria dinámica. El programa principal atiende la bandera en el ciclo.
pir_evento = False      # bandera levantada por la ISR
contador_irq = 0        # cantidad de interrupciones atendidas

def isr_pir(pin):
    """ISR: se ejecuta sola en cada flanco de subida del PIR."""
    global pir_evento
    pir_evento = True

pir.irq(trigger=Pin.IRQ_RISING, handler=isr_pir)

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

# ==================== CONTROL DEL 74HC595 ====================
estado_leds = 0b00000000   # bit 0 = Q0 ... bit 7 = Q7

def actualizar_595():
    """Envía el byte estado_leds al 74HC595 (primero Q7, al final Q0)."""
    stcp.value(0)
    for i in range(7, -1, -1):
        ds.value((estado_leds >> i) & 1)
        shcp.value(1)
        shcp.value(0)
    stcp.value(1)   # el latch pasa los bits a las salidas
    stcp.value(0)

def poner_led(bit, encendido):
    """Enciende o apaga un solo LED sin afectar a los demás."""
    global estado_leds
    if encendido:
        estado_leds |= (1 << bit)
    else:
        estado_leds &= ~(1 << bit)
    estado_leds &= 0xFF
    actualizar_595()

def apagar_todos():
    global estado_leds
    estado_leds = 0
    actualizar_595()

# ==================== LECTURA DE SENSORES ====================
def medir_distancia_cm():
    """Devuelve la distancia del HC-SR04 en cm, o None si no hay eco."""
    trig.value(0)
    time.sleep_us(2)
    trig.value(1)
    time.sleep_us(10)
    trig.value(0)
    duracion = time_pulse_us(echo, 1, 30000)  # microsegundos (30 ms de límite)
    if duracion < 0:
        return None
    return duracion * 0.0343 / 2

# (la lectura del LDR vive ahora en sensor_ldr.py -> sensor_ldr.leer())

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
            poner_led(z["bit"], True)
            z["luz"] = True
            print("[{}] Luz ENCENDIDA".format(z["nombre"]))
            registrar_evento(z["nombre"], "LUZ_ENCENDIDA")
    elif z["luz"]:
        if time.ticks_diff(ahora, z["ultima"]) >= config.TIEMPO_APAGADO * 1000:
            poner_led(z["bit"], False)
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
        poner_led(z["bit"], True)
        z["luz"] = True
        print("[{}] Luz ENCENDIDA".format(z["nombre"]))
        registrar_evento(z["nombre"], "LUZ_ENCENDIDA")
    elif not oscuro and z["oscuro"]:
        print("[{}] Luz ambiente suficiente (LDR = {})".format(z["nombre"], valor))
        registrar_evento(z["nombre"], "LUZ_SUFICIENTE", valor)
        poner_led(z["bit"], False)
        z["luz"] = False
        print("[{}] Luz APAGADA".format(z["nombre"]))
        registrar_evento(z["nombre"], "LUZ_APAGADA")
    z["oscuro"] = oscuro

# ==================== PROGRAMA PRINCIPAL ====================
apagar_todos()   # todos los LEDs apagados al iniciar

print("=================================")
print(" CASA INTELIGENTE - ESP32")
print("=================================")
print("Sistema iniciado correctamente")
print("Lectura inicial del LDR: {} (UMBRAL_LUZ = {})\n".format(sensor_ldr.leer(), config.UMBRAL_LUZ))

ultimo_debug = time.ticks_ms()

# Calentamiento del HC-SR04: se descarta la primera medición y se espera
# a que termine cualquier eco pendiente (el sensor necesita ~60 ms entre mediciones).
medir_distancia_cm()
time.sleep_ms(60)

while True:
    # Sala: PIR (por interrupción de hardware + lectura del nivel)
    hubo_irq = pir_evento
    if hubo_irq:
        pir_evento = False          # se atiende la bandera de la ISR
        contador_irq += 1
        print("[SALA] Interrupcion de hardware del PIR (IRQ #{})".format(contador_irq))
        registrar_evento("SALA", "IRQ_PIR", contador_irq)
    controlar_zona_presencia(sala, hubo_irq or pir.value() == 1)

    # Habitación 1: HC-SR04
    distancia = medir_distancia_cm()
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