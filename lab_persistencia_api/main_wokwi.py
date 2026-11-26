# Dispositivo que envia sus registros por HTTP (ESP32 en Wokwi). Completa los TODO 15 y 16.
# (En Wokwi: pega este contenido en la pestana main.py, junto con red.py)
from machine import Pin, ADC, time_pulse_us
from time import sleep, sleep_us, ticks_ms, ticks_diff
from red import conectar_wifi
try:
    import urequests as requests
except ImportError:
    import requests

# Wokwi no alcanza "localhost": usa un servicio publico que acepte POST (httpbin.org/post devuelve el eco).
URL = "https://httpbin.org/post"
API_KEY = "clave-curso"
INTERVALO = 10000

DISPOSITIVO = "demo-sala-francesco"
DISTANCIA_PRESENCIA = 100   # cm, igual que firmware/config.py
UMBRAL_LUZ = 2000           # ADC; en Wokwi la oscuridad da valores altos

sensor = ADC(Pin(34))       # LDR (Habitacion 2)
sensor.atten(ADC.ATTN_11DB)
pir = Pin(13, Pin.IN)       # PIR (Sala)
trig = Pin(14, Pin.OUT)     # HC-SR04 (Habitacion 1)
echo = Pin(12, Pin.IN)
led_envio = Pin(5, Pin.OUT)
fallos = 0


def medir_cm():
    """Distancia del HC-SR04 en cm, o None si no hay eco o esta fuera de 2-400 cm."""
    trig.value(0)
    sleep_us(2)
    trig.value(1)
    sleep_us(10)
    trig.value(0)
    duracion = time_pulse_us(echo, 1, 30000)
    if duracion < 0:
        return None
    distancia = round(duracion * 0.0343 / 2, 1)
    return distancia if 2 <= distancia <= 400 else None


def armar_cuerpo():
    """Devuelve el diccionario con los campos de TU proyecto (los mismos nombres de proyecto.py)."""
    movimiento = pir.value()
    ldr = sensor.read()
    distancia = medir_cm()
    cuerpo = {
        "dispositivo": DISPOSITIVO,
        "pir": movimiento,
        "ldr_adc": ldr,
        "luz_sala": 1 if movimiento else 0,
        "luz_habitacion_1": 1 if distancia is not None and distancia < DISTANCIA_PRESENCIA else 0,
        "luz_habitacion_2": 1 if ldr > UMBRAL_LUZ else 0,
    }
    if distancia is not None:
        cuerpo["distancia_cm"] = distancia
    return cuerpo


def enviar(cuerpo):
    # TODO 15: envia el cuerpo con requests.post(URL, json=cuerpo, headers={"X-API-Key": API_KEY}).
    #          Imprime el codigo de estado y devuelve True solo si es 200 o 201.
    #          Captura OSError (sin red, DNS, tiempo agotado): imprime el error y devuelve False.
    #          Cierra SIEMPRE la respuesta con close() (usa finally).
    return False


if not conectar_wifi():
    print("Sin Wi-Fi: reinicia la simulacion")
else:
    ultimo = ticks_ms() - INTERVALO
    while True:
        if ticks_diff(ticks_ms(), ultimo) >= INTERVALO:
            ultimo = ticks_ms()
            cuerpo = armar_cuerpo()
            print("Enviando", cuerpo)
            # TODO 16: enciende led_envio solo si el envio fue correcto; si falla, apagalo y cuenta los fallos
            #          seguidos. Tras 3 fallos seguidos imprime un aviso.
            led_envio.value(1 if enviar(cuerpo) else 0)
        sleep(0.1)
