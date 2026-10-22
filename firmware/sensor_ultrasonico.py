# sensor_ultrasonico.py: Habitación 1. Medición de distancia con el HC-SR04.
# Este archivo SOLO mide. Decidir si "hay presencia" (distancia < DISTANCIA_PRESENCIA)
# y prender la luz es responsabilidad de main.py (más adelante, de logica.py).

from machine import Pin, time_pulse_us
import time
import config

# Los pines vienen de config.py: así Wokwi y la placa real pueden usar pines distintos.
_trig = Pin(config.PIN_TRIG, Pin.OUT)   # TRIG: nosotros mandamos el pulso
_echo = Pin(config.PIN_ECHO, Pin.IN)    # ECHO: el sensor nos devuelve el tiempo

TIMEOUT_US = 30000   # límite de espera del eco (30 ms ≈ 5 m); si se pasa, no hay eco


def medir_cm():
    """Devuelve la distancia del HC-SR04 en cm, o None si no hay eco."""
    _trig.value(0)
    time.sleep_us(2)
    _trig.value(1)
    time.sleep_us(10)      # pulso de 10 µs: le ordena al sensor que mida
    _trig.value(0)
    duracion = time_pulse_us(_echo, 1, TIMEOUT_US)  # microsegundos que ECHO estuvo en 1
    if duracion < 0:       # -1 o -2: se acabó el tiempo sin recibir eco
        return None
    return duracion * 0.0343 / 2   # velocidad del sonido (cm/µs), ida y vuelta -> /2