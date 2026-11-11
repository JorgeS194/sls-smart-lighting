# sensor_pir.py: Sala. Sensor PIR de movimiento con interrupción de hardware.
# Este archivo SOLO detecta. Decidir si "hay presencia" y prender la luz
# (con el temporizador de apagado) es responsabilidad de main.py
# (más adelante, de logica.py y actuador_leds.py).

from machine import Pin
import config

# El pin viene de config.py: así Wokwi y la placa real pueden usar pines distintos.
_pir = Pin(config.PIN_PIR, Pin.IN)   # salida digital del PIR

# ==================== INTERRUPCIÓN DE HARDWARE ====================
# El PIR avisa por interrupción (flanco de subida en PIN_PIR). La rutina de
# interrupción (ISR) solo levanta una bandera: es corta y no imprime ni usa
# memoria dinámica. El programa principal consulta la bandera con
# hubo_interrupcion() en cada vuelta del ciclo.
_evento = False      # bandera levantada por la ISR
_contador = 0        # cantidad de interrupciones atendidas


def _isr(pin):
    """ISR: se ejecuta sola en cada flanco de subida del PIR."""
    global _evento
    _evento = True


_pir.irq(trigger=Pin.IRQ_RISING, handler=_isr)


def hubo_interrupcion():
    """True UNA sola vez por interrupción: atiende (baja) la bandera de la ISR."""
    global _evento, _contador
    if _evento:
        _evento = False
        _contador += 1
        return True
    return False


def contador():
    """Cantidad de interrupciones atendidas desde el arranque."""
    return _contador


def hay_movimiento():
    """Lectura del nivel actual del PIR: True mientras la salida siga en 1."""
    return _pir.value() == 1