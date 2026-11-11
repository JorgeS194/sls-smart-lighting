"""Contrato firmware → backend y API HTTP local. No usa brokers externos."""
import json
import sys
import tempfile
import threading
import types
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from estado import Almacen, validar
from servidor import crear_servidor


def evento(secuencia=1, **cambios):
    return dict({"version": 1, "dispositivo": "prueba", "sesion": "arranque-1",
                 "secuencia": secuencia, "tiempo_ms": 1000 * secuencia,
                 "zona": "HABITACION 1", "sensor": "HC-SR04",
                 "evento": "PRESENCIA", "valor": 60, "luz": True}, **cambios)


class PruebaAlmacen(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ruta = Path(self.tmp.name) / "test.sqlite3"
        self.almacen = Almacen(self.ruta)
        self.addCleanup(lambda: self.almacen.cerrar())

    def test_deduplica_y_conserva_lectura_al_apagar(self):
        self.assertEqual(self.almacen.agregar([evento(), evento()]), 1)
        self.almacen.agregar([evento(2, evento="LUZ_APAGADA", valor="", luz=False)])
        estado = self.almacen.estado()
        self.assertEqual(estado["total_eventos"], 2)
        self.assertFalse(estado["zonas"][1]["luz"])
        self.assertEqual(estado["zonas"][1]["lectura"], 60)

    def test_reenvio_atrasado_no_revierte_estado(self):
        self.almacen.agregar([evento(3, luz=False), evento(1, luz=True)])
        self.assertFalse(self.almacen.estado()["zonas"][1]["luz"])

    def test_sesion_nueva_admite_reinicio_de_secuencia(self):
        self.almacen.agregar([evento(300, luz=True), evento(1, sesion="arranque-2", luz=False)])
        self.almacen.agregar([evento(301, luz=True)])
        self.assertFalse(self.almacen.estado()["zonas"][1]["luz"])

    def test_lote_invalido_no_guarda_parcialmente(self):
        with self.assertRaises(ValueError):
            self.almacen.agregar([evento(), evento(2, sensor="LDR")])
        self.assertEqual(self.almacen.estado()["total_eventos"], 0)

    def test_rechaza_tipos_incorrectos(self):
        for cambios in ({"zona": []}, {"evento": []}, {"valor": float("nan")},
                        {"luz": 1}, {"version": True}, {"secuencia": 2**80}, {"valor": None}):
            with self.subTest(cambios=cambios), self.assertRaises(ValueError):
                validar(evento(**cambios))

    def test_persistencia_entre_instancias(self):
        self.almacen.agregar([evento()])
        otro = Almacen(self.ruta)
        try:
            self.assertEqual(otro.estado()["total_eventos"], 1)
        finally:
            otro.cerrar()

    def test_receptor_mqtt_solo_suscribe_valida_y_deduplica(self):
        import mqtt_receptor
        cliente = Mock()
        paho = types.ModuleType("paho")
        mqtt = types.ModuleType("paho.mqtt")
        client_module = types.ModuleType("paho.mqtt.client")
        paho.mqtt = mqtt
        mqtt.client = client_module
        client_module.Client = Mock(return_value=cliente)
        client_module.CallbackAPIVersion = types.SimpleNamespace(VERSION2=2)
        with patch.dict(sys.modules, {"paho": paho, "paho.mqtt": mqtt, "paho.mqtt.client": client_module}):
            estado = {}
            mqtt_receptor.conectar("broker-falso.invalid", 1883, "prueba/eventos", self.almacen, estado)
        cliente.on_connect(cliente, None, None, types.SimpleNamespace(is_failure=False), None)
        cliente.subscribe.assert_called_once_with("prueba/eventos", qos=1)
        mensaje = types.SimpleNamespace(payload=json.dumps(evento()).encode())
        cliente.on_message(cliente, None, mensaje)
        cliente.on_message(cliente, None, mensaje)
        self.assertEqual(self.almacen.estado()["total_eventos"], 1)
        cliente.on_message(cliente, None, types.SimpleNamespace(payload=b"{}"))
        self.assertIn("rechazado", estado["error"])
        cliente.publish.assert_not_called()


class PruebaAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.servidor = crear_servidor(0, cls.tmp.name)
        cls.hilo = threading.Thread(target=cls.servidor.serve_forever, daemon=True)
        cls.hilo.start()
        cls.base = "http://127.0.0.1:" + str(cls.servidor.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.hilo.join()
        cls.servidor.server_close()
        cls.servidor.almacen.cerrar()
        cls.tmp.cleanup()

    def obtener(self, ruta):
        return urlopen(self.base + ruta, timeout=3)

    def test_archivos_y_modulos_se_sirven_con_tipo_correcto(self):
        for ruta, tipo in (("/", "text/html"), ("/styles.css", "text/css"), ("/app.mjs", "javascript")):
            with self.subTest(ruta=ruta), self.obtener(ruta) as respuesta:
                self.assertEqual(respuesta.status, 200)
                self.assertIn(tipo, respuesta.headers["Content-Type"])
                self.assertIn("frame-ancestors 'none'", respuesta.headers["Content-Security-Policy"])

    def test_importa_y_exporta_evento_real(self):
        request = Request(self.base + "/api/eventos", data=json.dumps(evento()).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=3) as respuesta:
            self.assertEqual(json.load(respuesta)["agregados"], 1)
        with self.obtener("/api/estado") as respuesta:
            estado = json.load(respuesta)
            self.assertEqual(estado["total_eventos"], 1)
            self.assertFalse(estado["mqtt"]["configurado"])
        with self.obtener("/api/exportar.csv") as respuesta:
            self.assertIn("HC-SR04", respuesta.read().decode("utf-8-sig"))

    def test_rechaza_origen_externo_y_json_invalido(self):
        for headers, payload, status in (({"Content-Type": "application/json", "Origin": "https://ajeno.invalid"}, b"{}", 403),
                                         ({"Content-Type": "application/json"}, b"no-json", 400),
                                         ({"Content-Type": "text/plain"}, b"{}", 415)):
            request = Request(self.base + "/api/eventos", data=payload, headers=headers, method="POST")
            with self.subTest(status=status), self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, status)

    def test_no_expone_archivos_fuera_del_dashboard(self):
        with self.assertRaises(HTTPError) as error:
            self.obtener("/../firmware/config.py")
        self.assertEqual(error.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
