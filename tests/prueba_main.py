"""Banco de pruebas: ejecuta main.py en CPython con un ESP32 simulado.

Simula el reloj, los pines, el ADC y el HC-SR04 para verificar que
(1) la logica original sigue igual, (2) la interrupcion del PIR se atiende y
(3) el bloque CSV, una vez descomentado, genera historial.csv.
"""
import os
import re
import sys
import tempfile
import time
import types

CICLOS = 150
INICIO_BLOQUE = ">>> INICIO CSV"
FIN_BLOQUE = "<<< FIN CSV"


class FinPrueba(BaseException):
    pass


def descomentar_csv(fuente):
    salida, dentro = [], False
    for linea in fuente.splitlines():
        if INICIO_BLOQUE in linea:
            dentro = True
        elif FIN_BLOQUE in linea:
            dentro = False
        elif dentro:
            linea = re.sub(r"^(\s*)# ?", r"\1", linea, count=1)
        salida.append(linea)
    return "\n".join(salida) + "\n"


def ejecutar(fuente, etiqueta):
    estado = {"ciclo": 0, "ms": 0, "pines": {}, "log": []}

    # ---- escenario (depende del ciclo) ----
    def pir_nivel():
        return 1 if 10 <= estado["ciclo"] < 20 else 0       # nivel alto 10-19

    def distancia():
        return 50.0 if 20 <= estado["ciclo"] < 60 else None  # sin eco fuera

    def ldr_valor():
        return 3000 if 70 <= estado["ciclo"] <= 120 else 500

    # ---- modulo machine falso ----
    class Pin:
        IN, OUT, IRQ_RISING = 0, 1, 1

        def __init__(self, num, modo=None):
            self.num, self.handler, self.nivel = num, None, 0
            estado["pines"][num] = self

        def value(self, v=None):
            if v is None:
                return pir_nivel() if self.num == 13 else self.nivel
            self.nivel = v

        def irq(self, trigger=None, handler=None):
            self.handler = handler

    class ADC:
        ATTN_11DB = 3

        def __init__(self, pin):
            pass

        def atten(self, a):
            pass

        def read(self):
            return ldr_valor()

    def time_pulse_us(pin, nivel, timeout):
        d = distancia()
        return -1 if d is None else int(d * 2 / 0.0343)

    machine = types.ModuleType("machine")
    machine.Pin, machine.ADC, machine.time_pulse_us = Pin, ADC, time_pulse_us
    sys.modules["machine"] = machine

    # ---- extensiones MicroPython del modulo time ----
    time.ticks_ms = lambda: estado["ms"]
    time.ticks_diff = lambda a, b: a - b
    time.sleep_us = lambda us: None

    def sleep_ms(ms):
        estado["ms"] += ms
        estado["ciclo"] += 1
        # pulso corto del PIR: la interrupcion ocurre pero el nivel ya bajo
        if estado["ciclo"] == 40:
            estado["pines"][13].handler(estado["pines"][13])
        if estado["ciclo"] == 10:
            estado["pines"][13].handler(estado["pines"][13])
        if estado["ciclo"] >= CICLOS:
            raise FinPrueba()

    time.sleep_ms = sleep_ms

    import io
    import contextlib
    buf = io.StringIO()
    ns = {"__name__": "__main__"}
    with contextlib.redirect_stdout(buf):
        try:
            exec(compile(fuente, etiqueta, "exec"), ns)
        except FinPrueba:
            pass
    return buf.getvalue(), ns


if __name__ == "__main__":
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware", "main.py")
    with open(ruta, encoding="utf-8") as f:
        original = f.read()

    trabajo = tempfile.mkdtemp()
    os.chdir(trabajo)

    print("=== PRUEBA A: main.py tal como se entrega (CSV comentado) ===")
    salida, ns = ejecutar(original, "main.py")
    print(salida)
    print("IRQ atendidas:", ns["contador_irq"],
          "| eventos en RAM:", len(ns["historial"]),
          "| historial.csv existe:", os.path.exists("historial.csv"))

    print("\n=== PRUEBA B: CSV descomentado (como en un ESP32 real) ===")
    salida_b, ns_b = ejecutar(descomentar_csv(original), "main_csv.py")
    print("Salida de consola identica a la prueba A:", salida == salida_b)
    print("historial.csv existe:", os.path.exists("historial.csv"))
    with open("historial.csv") as f:
        print(f.read())
