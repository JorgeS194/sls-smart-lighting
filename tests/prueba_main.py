"""Banco de pruebas: ejecuta main.py en CPython con un ESP32 simulado.

Simula el reloj, los pines, el ADC y el HC-SR04 para verificar que
(1) la logica original sigue igual, (2) la interrupcion del PIR se atiende y
(3) el bloque CSV, una vez descomentado, genera historial.csv.
"""
import os
import re
import sys
import tempfile
import types
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

FIRMWARE = Path(__file__).resolve().parents[1] / "firmware"
MODULOS = tuple(p.stem for p in FIRMWARE.glob("*.py") if p.stem != "main")

CICLOS = 150
INICIO_BLOQUE = ">>> INICIO CSV"
FIN_BLOQUE = "<<< FIN CSV"


class FinPrueba(BaseException):
    pass


@contextmanager
def directorio(ruta):
    anterior = os.getcwd()
    try:
        os.chdir(ruta)
        yield
    finally:
        os.chdir(anterior)


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


def ejecutar(fuente, etiqueta, csv=False):
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

    # ---- extensiones MicroPython del modulo time ----
    reloj = types.ModuleType("time")
    reloj.ticks_ms = lambda: estado["ms"]
    reloj.ticks_diff = lambda a, b: a - b
    reloj.sleep_us = lambda us: None

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

    reloj.sleep_ms = sleep_ms

    import io
    import contextlib
    buf = io.StringIO()
    ns = {"__name__": "__main__"}
    # Cada corrida importa estado nuevo y restaura los módulos y rutas del proceso.
    with patch.dict(sys.modules), patch.object(sys, "path", [str(FIRMWARE)] + sys.path), contextlib.redirect_stdout(buf):
        for nombre in MODULOS:
            sys.modules.pop(nombre, None)
        sys.modules.update(machine=machine, time=reloj)
        if csv:
            modulo = types.ModuleType("historial")
            sys.modules["historial"] = modulo
            codigo = descomentar_csv((FIRMWARE / "historial.py").read_text(encoding="utf-8"))
            exec(compile(codigo, "historial_csv.py", "exec"), modulo.__dict__)
        try:
            exec(compile(fuente, etiqueta, "exec"), ns)
        except FinPrueba:
            pass
    return buf.getvalue(), ns


if __name__ == "__main__":
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "firmware", "main.py")
    with open(ruta, encoding="utf-8") as f:
        original = f.read()

    anterior = os.getcwd()
    try:
        with tempfile.TemporaryDirectory() as trabajo, directorio(trabajo):
            salida, ns = ejecutar(original, "main.py")
            eventos = ns["historial"].eventos()
            assert ns["sensor_pir"].contador() == 2
            assert not os.path.exists("historial.csv")
            assert len(eventos) == 16, eventos
            assert [e[3] for e in eventos if e[2] == "IRQ_PIR"] == [1, 2]
            assert [(e[1], e[2]) for e in eventos] == [
                ("SALA", "IRQ_PIR"), ("SALA", "PRESENCIA"),
                ("SALA", "LUZ_ENCENDIDA"), ("SALA", "SIN_PRESENCIA"),
                ("HABITACION 1", "PRESENCIA"), ("HABITACION 1", "LUZ_ENCENDIDA"),
                ("SALA", "IRQ_PIR"), ("SALA", "PRESENCIA"),
                ("SALA", "SIN_PRESENCIA"), ("HABITACION 1", "SIN_PRESENCIA"),
                ("HABITACION 2", "OSCURIDAD"), ("HABITACION 2", "LUZ_ENCENDIDA"),
                ("SALA", "LUZ_APAGADA"), ("HABITACION 1", "LUZ_APAGADA"),
                ("HABITACION 2", "LUZ_SUFICIENTE"), ("HABITACION 2", "LUZ_APAGADA")]
            assert eventos[12][0] - eventos[7][0] == ns["config"].TIEMPO_APAGADO * 1000
            assert eventos[13][0] - eventos[4][0] >= ns["config"].TIEMPO_APAGADO * 1000
            for zona in ("SALA", "HABITACION 1", "HABITACION 2"):
                assert sum(e[1:3] == (zona, "LUZ_ENCENDIDA") for e in eventos) == 1
                assert sum(e[1:3] == (zona, "LUZ_APAGADA") for e in eventos) == 1
            assert ns["actuador_leds"]._estado == 0
            salida_b, ns_b = ejecutar(original, "main_csv.py", csv=True)
            assert salida == salida_b
            assert eventos == ns_b["historial"].eventos()
            with open("historial.csv") as f:
                filas = f.read().splitlines()
            assert filas == ["tiempo_ms,zona,evento,valor"] + [
                ",".join(map(str, evento)) for evento in eventos]
            print(salida)
            print("OK: dos IRQ, 16 eventos, LEDs apagados y CSV idéntico al historial RAM")
            os.chdir(anterior)
    finally:
        os.chdir(anterior)
