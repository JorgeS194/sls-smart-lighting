import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.main import Servicio


class PruebaMonitor(unittest.TestCase):
    def setUp(self):
        carpeta = TemporaryDirectory()
        self.addCleanup(carpeta.cleanup)
        self.servicio = Servicio(Path(carpeta.name), silencio_s=7)
        self.ms = 0
        self.servicio.monitor.reloj_ms = lambda: self.ms
        self.servicio.cambiar_conexion(True)

    def enviar(self, tipo, dispositivo="esp32", sesion="a", **campos):
        self.servicio.recibir_mqtt(
            f"equipo/{dispositivo}/{tipo}",
            dict(version=2, dispositivo=dispositivo, sesion=sesion, **campos),
            "equipo",
        )

    def telemetria(self, intervalo=2000, **campos):
        self.enviar("telemetria", secuencia=1, intervalo_ms=intervalo,
                    lecturas=dict(pir=0, ldr_adc=100, distancia_cm=50),
                    luces=dict(SALA=False, HABITACION_1=False, HABITACION_2=False),
                    **campos)

    def avanzar(self, ms):
        self.ms += ms
        self.servicio.revisar_comunicacion()

    def eventos(self):
        with self.servicio.monitor.archivo.open(newline="", encoding="utf-8") as archivo:
            return list(csv.DictReader(archivo))

    def test_transiciones_y_duplicados(self):
        self.enviar("estado", estado="online")
        self.telemetria()
        self.avanzar(6999)
        self.assertEqual(len(self.eventos()), 1)
        self.avanzar(1)
        self.avanzar(1000)
        self.enviar("estado", estado="online")
        self.telemetria()
        self.telemetria()
        self.enviar("estado", estado="offline")
        self.enviar("estado", estado="offline")
        self.avanzar(8000)
        eventos = self.eventos()
        self.assertEqual([e["tipo"] for e in eventos],
                         ["ONLINE", "SIN_DATOS", "ONLINE", "OFFLINE"])
        self.assertEqual(set(eventos[0]), {"fecha", "tipo", "gravedad", "detalle"})

    def test_intervalo_por_dispositivo_y_perdida_del_receptor(self):
        self.telemetria(intervalo=3000)
        self.telemetria(dispositivo="otro")
        self.avanzar(7000)
        self.assertIn("otro", self.eventos()[-1]["detalle"])
        self.assertEqual(len(self.eventos()), 3)
        self.servicio.cambiar_conexion(False)
        self.avanzar(30000)
        self.assertEqual(len(self.eventos()), 3)
        self.servicio.cambiar_conexion(True)
        self.avanzar(8999)
        self.assertEqual(len(self.eventos()), 3)
        self.avanzar(1)
        self.assertIn("9000 ms", self.eventos()[-1]["detalle"])

    def test_nueva_sesion_y_estado_invalido(self):
        self.enviar("estado", estado="online")
        self.avanzar(7000)
        self.telemetria(sesion="b")
        self.enviar("estado", sesion="a", estado="offline")
        with self.assertRaises(ValueError):
            self.enviar("estado", sesion="b", estado="desconocido")
        self.assertEqual([e["tipo"] for e in self.eventos()], ["SIN_DATOS", "ONLINE"])
