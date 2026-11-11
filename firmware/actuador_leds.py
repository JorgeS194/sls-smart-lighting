# actuador_leds.py: LEDs de las zonas, controlados con el 74HC595.
# Este archivo SOLO enciende y apaga LEDs. Decidir CUÁNDO hacerlo (presencia,
# oscuridad, temporizador) es responsabilidad de main.py (más adelante, de logica.py).

from machine import Pin
import config

# Los pines vienen de config.py: así Wokwi y la placa real pueden usar pines distintos.
_ds = Pin(config.PIN_DS, Pin.OUT)       # 74HC595: DS   (datos)
_stcp = Pin(config.PIN_STCP, Pin.OUT)   # 74HC595: STCP (latch)
_shcp = Pin(config.PIN_SHCP, Pin.OUT)   # 74HC595: SHCP (reloj)

# El 74HC595 solo recibe datos: no se puede preguntar qué LEDs están prendidos.
# Por eso guardamos aquí una copia del byte que enviamos (bit 0 = Q0 ... bit 7 = Q7).
_estado = 0b00000000


def _actualizar():
    """Envía el byte _estado al 74HC595 (primero Q7, al final Q0)."""
    _stcp.value(0)
    for i in range(7, -1, -1):
        _ds.value((_estado >> i) & 1)
        _shcp.value(1)
        _shcp.value(0)
    _stcp.value(1)   # el latch pasa los bits a las salidas
    _stcp.value(0)


def poner(bit, encendido):
    """Enciende o apaga un solo LED (salida Qbit) sin afectar a los demás."""
    global _estado
    if encendido:
        _estado |= (1 << bit)
    else:
        _estado &= ~(1 << bit)
    _estado &= 0xFF
    _actualizar()


def apagar_todos():
    """Apaga los 8 LEDs a la vez."""
    global _estado
    _estado = 0
    _actualizar()