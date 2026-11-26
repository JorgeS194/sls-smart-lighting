# Dispositivo que envia sus registros por HTTP (ESP32 en Wokwi). Completa los TODO 15 y 16.
# (En Wokwi: pega este contenido en la pestana main.py, junto con red.py)
from machine import Pin, ADC
from time import sleep, ticks_ms, ticks_diff
from red import conectar_wifi
try:
    import urequests as requests
except ImportError:
    import requests

# Wokwi no alcanza "localhost": usa un servicio publico que acepte POST (httpbin.org/post devuelve el eco).
URL = "https://httpbin.org/post"
API_KEY = "clave-curso"
INTERVALO = 10000

sensor = ADC(Pin(34))
sensor.atten(ADC.ATTN_11DB)
led_envio = Pin(5, Pin.OUT)
fallos = 0


def armar_cuerpo():
    """Devuelve el diccionario con los campos de TU proyecto (los mismos nombres de proyecto.py).
    Ejemplo del riego: humedad leida del potenciometro, bomba y modo."""
    humedad = round(sensor.read() / 4095 * 100)
    return {"humedad": humedad, "bomba": 1 if humedad < 40 else 0, "modo": "AUTO", "umbral": 40}


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
