"""Disponibilidad MQTT y vigencia de la telemetría por dispositivo."""
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from time import monotonic_ns
from typing import Optional

LOG = logging.getLogger(__name__)
GRAVEDADES = {"ONLINE": "INFO", "SIN_DATOS": "ADVERTENCIA", "OFFLINE": "ERROR"}


@dataclass
class Dispositivo:
    sesion: str
    desde_ms: int
    intervalo_ms: int = 2000
    estado: Optional[str] = None
    conectado: bool = True


class Monitor:
    def __init__(self, archivo, silencio_s, reloj_ms=None):
        if silencio_s < 6:
            raise ValueError("El tiempo de silencio debe ser de al menos 6 segundos")
        self.archivo = archivo
        self.silencio_ms = silencio_s * 1000
        self.reloj_ms = reloj_ms or (lambda: monotonic_ns() // 1_000_000)
        self.dispositivos = {}

    def _dispositivo(self, nombre, sesion):
        actual = self.dispositivos.get(nombre)
        if actual is None or actual.sesion != sesion:
            estado = actual.estado if actual else None
            actual = Dispositivo(sesion, self.reloj_ms(), estado=estado)
            self.dispositivos[nombre] = actual
        return actual

    def _transicion(self, nombre, actual, estado, motivo):
        if actual.estado == estado:
            return
        detalle = f"{nombre} (sesión {actual.sesion}): {motivo}"
        nuevo = not self.archivo.exists() or self.archivo.stat().st_size == 0
        with self.archivo.open("a", newline="", encoding="utf-8") as archivo:
            escritor = csv.writer(archivo)
            if nuevo:
                escritor.writerow(("fecha", "tipo", "gravedad", "detalle"))
            escritor.writerow((datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                                estado, GRAVEDADES[estado], detalle))
        actual.estado = estado
        LOG.log({"ONLINE": logging.INFO, "SIN_DATOS": logging.WARNING,
                 "OFFLINE": logging.ERROR}[estado], "%s %s", estado, detalle)

    def disponibilidad(self, nombre, sesion, estado):
        anterior = self.dispositivos.get(nombre)
        if estado == "offline" and anterior and anterior.sesion != sesion:
            return
        actual = self._dispositivo(nombre, sesion)
        if estado == "offline":
            self._transicion(nombre, actual, "OFFLINE", "Last Will recibido")
            actual.conectado = False
        elif not actual.conectado:
            actual.conectado = True
            actual.desde_ms = self.reloj_ms()

    def telemetria(self, nombre, sesion, intervalo_ms):
        actual = self._dispositivo(nombre, sesion)
        self._transicion(nombre, actual, "ONLINE", "telemetría válida recibida")
        actual.conectado = True
        actual.intervalo_ms = intervalo_ms
        actual.desde_ms = self.reloj_ms()

    def reiniciar_plazos(self):
        ahora = self.reloj_ms()
        for actual in self.dispositivos.values():
            actual.desde_ms = ahora

    def revisar(self):
        ahora = self.reloj_ms()
        for nombre, actual in self.dispositivos.items():
            umbral = max(self.silencio_ms, 3 * actual.intervalo_ms)
            if actual.conectado and ahora - actual.desde_ms >= umbral:
                self._transicion(nombre, actual, "SIN_DATOS",
                                 f"sin telemetría válida durante al menos {umbral} ms")
