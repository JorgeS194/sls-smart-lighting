import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .main import Servicio, crear_handler
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
