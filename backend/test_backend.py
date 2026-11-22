import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch
from .main import Servicio, conectar_mqtt, crear_handler
from .receptor import validar_mensaje


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent / 'datos')
        self.addCleanup(self.tmp.cleanup)
        self.servicio = Servicio(self.tmp.name)

    def lectura(self, **campos):
        return dict({'zona': 'SALA', 'sensor': 'PIR', 'valor': 1,
                     'evento': 'PRESENCIA'}, **campos)

    def test_validacion(self):
        for dato in (b'{', [], self.lectura(valor=True), self.lectura(valor=float('nan')),
                     self.lectura(valor=2), self.lectura(zona=[]),
                     self.lectura(sensor='LDR'), self.lectura(evento={}), self.lectura(luz=1)):
            with self.subTest(dato=dato), self.assertRaises(ValueError):
                validar_mensaje(dato)

    def test_reinicio_y_estado_observado(self):
        estado = self.servicio.recibir(self.lectura())
        self.assertIsNone(estado['zonas']['SALA']['luz'])
        self.servicio.recibir(self.lectura(evento='LUZ_ENCENDIDA'))
        self.servicio.recibir(self.lectura(valor=0, evento='SIN_PRESENCIA'))
        restaurado = Servicio(self.tmp.name)
        self.assertEqual(restaurado.estado['lecturas'], 3)
        self.assertTrue(restaurado.estado['zonas']['SALA']['luz'])
        self.assertEqual(len(restaurado.persistencia.historial(2, 'SALA')), 2)

    def test_histeresis(self):
        for valor, clase in ((2200, 'OSCURO'), (2000, 'OSCURO'), (1800, 'CLARO')):
            estado = self.servicio.recibir({'zona': 'HABITACION_2', 'sensor': 'LDR', 'valor': valor})
            self.assertEqual(estado['zonas']['HABITACION_2']['clasificacion'], clase)

    def test_comando_desconectado(self):
        with self.assertRaises(ConnectionError):
            self.servicio.comando({'zona': 'SALA', 'accion': 'apagar'})
        self.assertIsNone(self.servicio.estado['zonas']['SALA']['luz'])

    def comprobar_topico_comandos(self, dispositivo, topico_esperado):
        paho = ModuleType("paho")
        paho.mqtt = ModuleType("paho.mqtt")
        paho.mqtt.client = MagicMock()
        modulos = {"paho": paho, "paho.mqtt": paho.mqtt, "paho.mqtt.client": paho.mqtt.client}
        args = SimpleNamespace(prefijo="utp/ds8/1gs133/sls-smart-lighting",
                               dispositivo_comandos=dispositivo, tls=False,
                               broker="localhost", puerto_mqtt=1883)
        with patch.dict(sys.modules, modulos):
            cliente = conectar_mqtt(self.servicio, args)
        cliente.publish.return_value.rc = 0
        self.servicio.cambiar_conexion(True)
        self.servicio.comando({"zona": "SALA", "accion": "apagar"})
        cliente.publish.assert_called_once()
        self.assertEqual(cliente.publish.call_args.args[0], topico_esperado)

    def test_comando_publica_en_topico_legado(self):
        self.comprobar_topico_comandos(None, "utp/ds8/1gs133/sls-smart-lighting/comandos")

    def test_comando_publica_en_topico_del_dispositivo(self):
        self.comprobar_topico_comandos(
            "demo-sala-francesco", "utp/ds8/1gs133/sls-smart-lighting/demo-sala-francesco/comandos"
        )

    def test_api_comandos_tres_zonas_errores_y_destino(self):
        self.servicio.mqtt = MagicMock()
        self.servicio.mqtt.publish.return_value.rc = 0
        self.servicio.conectado = True
        self.servicio.topico_comandos = "equipo/demo/comandos"
        servidor = ThreadingHTTPServer(("127.0.0.1", 0), crear_handler(self.servicio, "http://localhost:5173"))
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        base = f"http://127.0.0.1:{servidor.server_port}"
        self.addCleanup(hilo.join)
        self.addCleanup(servidor.server_close)
        self.addCleanup(servidor.shutdown)
        for destino in (None, "demo-sala-francesco"):
            self.servicio.dispositivo_comandos = destino
            with urlopen(base + "/api/salud") as r:
                salud = json.load(r)
            self.assertEqual(salud["dispositivo_comandos"], destino)
            self.assertTrue(salud["mqtt_configurado"])
            self.assertTrue(salud["mqtt_conectado"])
        self.servicio.modos = {"SALA": "manual"}
        self.servicio.ordenes = {"SALA": "confirmada"}
        with urlopen(base + "/api/estado") as r:
            estado = json.load(r)
        self.assertEqual(estado["zonas"]["SALA"]["modo"], "manual")
        self.assertEqual(estado["zonas"]["SALA"]["orden_id"], "confirmada")
        self.assertEqual(estado["zonas"]["HABITACION_1"]["modo"], "auto")
        for zona in ("SALA", "HABITACION_1", "HABITACION_2"):
            for accion in ("encender", "apagar", "auto"):
                with urlopen(Request(base + "/api/comandos", data=json.dumps(dict(zona=zona, accion=accion)).encode())) as r:
                    self.assertEqual(r.status, 202)
                    enviado = json.load(r)["comando"]
                self.assertEqual(enviado["zona"], zona)
                self.assertEqual(enviado["accion"], accion)
                self.assertEqual(self.servicio.mqtt.publish.call_args.kwargs, {"qos": 1, "retain": False})
        anteriores = self.servicio.mqtt.publish.call_count
        for comando in (dict(zona="OTRA", accion="encender"), dict(zona="SALA", accion="otra")):
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(base + "/api/comandos", data=json.dumps(comando).encode()))
            self.assertEqual(error.exception.code, 400)
            self.assertIn("error", json.load(error.exception))
            error.exception.close()
        self.servicio.conectado = False
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(base + "/api/comandos", data=b'{"zona":"SALA","accion":"encender"}'))
        self.assertEqual(error.exception.code, 503)
        self.assertIn("MQTT desconectado", json.load(error.exception)["error"])
        error.exception.close()
        self.assertEqual(self.servicio.mqtt.publish.call_count, anteriores)

    def test_api(self):
        servidor = ThreadingHTTPServer(('127.0.0.1', 0), crear_handler(self.servicio, 'http://localhost:5173'))
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        base = 'http://127.0.0.1:' + str(servidor.server_port)
        try:
            with urlopen(Request(base + '/api/lecturas', data=json.dumps(self.lectura()).encode())) as r:
                self.assertEqual(r.status, 201)
                self.assertEqual(r.headers['Access-Control-Allow-Origin'], 'http://localhost:5173')
            with urlopen(base + '/api/historial?limite=1') as r:
                self.assertEqual(len(json.load(r)['historial']), 1)
            for ruta, cuerpo, codigo in (('/api/historial?limite=0', None, 400),
                                        ('/api/lecturas', b'[]', 400),
                                        ('/api/comandos', b'{"zona":"SALA","accion":"apagar"}', 503),
                                        ('/noexiste', None, 404)):
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(base + ruta, data=cuerpo))
                self.assertEqual(error.exception.code, codigo)
                error.exception.close()
        finally:
            servidor.shutdown()
            servidor.server_close()
            hilo.join()


if __name__ == '__main__':
    unittest.main()
