# sensor_ldr.py: Habitación 2. Lectura del LDR (fotoresistencia) por el ADC.
# Este archivo SOLO mide. Decidir si "está oscuro" y prender la luz es
# responsabilidad de main.py (más adelante, de logica.py y actuador_leds.py).

from machine import Pin, ADC
import config

# El pin viene de config.py: así Wokwi y la placa real pueden usar pines distintos.
_adc = ADC(Pin(config.PIN_LDR))
_adc.atten(ADC.ATTN_11DB)   # rango completo de lectura (0 - 3.3 V)

MUESTRAS = 8   # cuántas lecturas se promedian para que el valor sea estable


def leer():
    """Promedio de varias lecturas para un valor estable (0-4095)."""
    suma = 0
    for _ in range(MUESTRAS):
        suma += _adc.read()
    return suma // MUESTRAS