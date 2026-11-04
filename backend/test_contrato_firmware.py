"""Paso 1: eventos de mensajes.py del PR #12 recibidos por el backend del PR #9."""
import tempfile
import unittest
from pathlib import Path

from .main import Servicio
from .receptor import validar_mensaje


def evento(zona="SALA", sensor="PIR", nombre="PRESENCIA", valor="", luz=True):
    return {"version": 1, "dispositivo": "casa-01", "sesion": "prueba",
            "secuencia": 1, "tiempo_ms": 1000, "zona": zona, "sensor": sensor,
            "evento": nombre, "valor": valor, "luz": luz}


class ContratoFirmwareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent / "datos")
        self.addCleanup(self.tmp.cleanup)
        self.servicio = Servicio(self.tmp.name)

    def test_conserva_contrato_original_de_lecturas(self):
        dato = {"zona": "HABITACION_1", "sensor": "HC-SR04", "valor": 95}
        self.assertEqual(validar_mensaje(dato), dict(dato, evento="LECTURA"))
        self.assertEqual(self.servicio.recibir(dato)["zonas"]["HABITACION_1"]["valor"], 95)

    def test_normaliza_nombres_del_firmware(self):
        for nombre, canonico, sensor, valor in (("HABITACION 1", "HABITACION_1", "HC-SR04", 60),
                                               ("HABITACION 2", "HABITACION_2", "LDR", 2593)):
            with self.subTest(zona=nombre):
                self.assertEqual(validar_mensaje(evento(nombre, sensor, valor=valor))["zona"], canonico)

    def test_sala_irq_no_es_una_lectura_ni_presencia(self):
        self.servicio.recibir({"zona": "SALA", "sensor": "PIR", "valor": 0, "luz": False})
        estado = self.servicio.recibir(evento(nombre="IRQ_PIR", valor=3, luz=False))
        self.assertEqual(estado["zonas"]["SALA"]["valor"], 0)
        self.assertEqual(estado["zonas"]["SALA"]["clasificacion"], "SIN_PRESENCIA")
        self.assertEqual(self.servicio.persistencia.historial(1)[0]["valor"], 3)

    def test_evento_de_luz_conserva_la_ultima_distancia(self):
        self.servicio.recibir(evento("HABITACION 1", "HC-SR04", valor=60))
        estado = self.servicio.recibir(evento("HABITACION 1", "HC-SR04", "LUZ_APAGADA", luz=False))
        self.assertFalse(estado["zonas"]["HABITACION_1"]["luz"])
        self.assertEqual(estado["zonas"]["HABITACION_1"]["valor"], 60)
        self.assertIsNone(self.servicio.persistencia.historial(1)[0]["valor"])

    def test_evento_sin_dato_no_inventa_una_lectura_inicial(self):
        estado = self.servicio.recibir(evento("HABITACION 2", "LDR", "LUZ_ENCENDIDA"))
        zona = estado["zonas"]["HABITACION_2"]
        self.assertIsNone(zona["valor"])
        self.assertIsNone(zona["clasificacion"])
        self.assertTrue(zona["luz"])

    def test_reinicio_reconstruye_eventos_con_valor_vacio_y_contadores(self):
        for dato in (evento(nombre="IRQ_PIR", valor=1, luz=False),
                     evento(), evento(nombre="LUZ_ENCENDIDA"),
                     evento(nombre="SIN_PRESENCIA"),
                     evento(nombre="LUZ_APAGADA", luz=False),
                     evento(nombre="IRQ_PIR", valor=2, luz=False)):
            self.servicio.recibir(dato)
        restaurado = Servicio(self.tmp.name)
        self.assertEqual(restaurado.estado, self.servicio.estado)
        self.assertIsNone(restaurado.estado["zonas"]["SALA"]["valor"])
        self.assertFalse(restaurado.estado["zonas"]["SALA"]["luz"])

    def test_eventos_presencia_sin_lectura_actualizan_clasificacion(self):
        for nombre in ("PRESENCIA", "SIN_PRESENCIA"):
            estado = self.servicio.recibir(evento("HABITACION 1", "HC-SR04", nombre))
            self.assertEqual(estado["zonas"]["HABITACION_1"]["clasificacion"], nombre)

    def test_conserva_lectura_ldr_e_histeresis_tras_cambio_de_luz(self):
        self.servicio.recibir(evento("HABITACION 2", "LDR", "OSCURIDAD", 2200))
        self.servicio.recibir(evento("HABITACION 2", "LDR", "LUZ_ENCENDIDA"))
        estado = self.servicio.recibir(evento("HABITACION 2", "LDR", "LECTURA", 2000))
        self.assertEqual(estado["zonas"]["HABITACION_2"]["clasificacion"], "OSCURO")

    def test_rechaza_ausencia_de_lectura_y_contadores_invalidos(self):
        for dato in (evento(nombre="LECTURA"), evento(nombre="IRQ_PIR"),
                     evento(nombre="IRQ_PIR", valor=True), evento(nombre="IRQ_PIR", valor=0),
                     evento("HABITACION 1", "HC-SR04", "IRQ_PIR", 3),
                     dict(evento(), version=2), dict(evento(), version=True),
                     evento("HABITACION 2", "LDR", "OSCURIDAD")):
            with self.subTest(dato=dato), self.assertRaises(ValueError):
                validar_mensaje(dato)


if __name__ == "__main__":
    unittest.main()
