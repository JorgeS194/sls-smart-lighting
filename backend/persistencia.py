"""Historial duradero y reconstrucción del estado al reiniciar."""
import csv
import json
import os
from collections import deque
from pathlib import Path
from .procesamiento import estado_inicial

CAMPOS = ("fecha_hora", "zona", "sensor", "valor", "evento", "clasificacion", "luz")


class Persistencia:
    def __init__(self, directorio):
        self.directorio = Path(directorio)
        self.directorio.mkdir(parents=True, exist_ok=True)
        self.csv = self.directorio / "historial.csv"
        self.json = self.directorio / "estado.json"

    def cargar(self):
        # CSV es la fuente de verdad si el proceso se interrumpe antes del snapshot.
        estado = estado_inicial()
        if self.csv.exists():
            with self.csv.open(newline="", encoding="utf-8") as archivo:
                for fila in csv.DictReader(archivo):
                    zona = estado["zonas"][fila["zona"]]
                    zona.update(sensor=fila["sensor"], valor=float(fila["valor"]),
                                clasificacion=fila["clasificacion"],
                                luz={"True": True, "False": False, "": None}[fila["luz"]],
                                ultima_actualizacion=fila["fecha_hora"])
                    estado["lecturas"] += 1
                    estado["ultima_actualizacion"] = fila["fecha_hora"]
        return estado

    def guardar(self, estado, fila):
        nuevo = not self.csv.exists() or self.csv.stat().st_size == 0
        with self.csv.open("a", newline="", encoding="utf-8") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=CAMPOS)
            if nuevo:
                escritor.writeheader()
            escritor.writerow(fila)
            archivo.flush()
            os.fsync(archivo.fileno())
        self.snapshot(estado)

    def snapshot(self, estado):
        temporal = self.json.with_suffix(".json.tmp")
        temporal.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporal, self.json)

    def historial(self, limite=100, zona=None):
        if not self.csv.exists():
            return []
        with self.csv.open(newline="", encoding="utf-8") as archivo:
            filas = deque((fila for fila in csv.DictReader(archivo)
                           if zona is None or fila["zona"] == zona), maxlen=limite)
        resultado = []
        for fila in reversed(filas):
            fila["valor"] = float(fila["valor"])
            fila["luz"] = {"True": True, "False": False, "": None}[fila["luz"]]
            resultado.append(fila)
        return resultado
