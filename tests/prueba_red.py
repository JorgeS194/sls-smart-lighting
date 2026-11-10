"""Pruebas sin internet: python -m unittest discover -s tests -p prueba_red.py -v."""
import contextlib
import importlib
import io
import json
import sys
import threading
import types
import unittest
from unittest.mock import patch

from prueba_main import ejecutar, FIRMWARE


class WiFiFalso:
    def __init__(self, conectado=False):
        self.conectado = conectado
        self.intentos = 0

    def active(self, activo):
        pass

    def isconnected(self):
        return self.conectado

    def connect(self, ssid, password):
        self.intentos += 1

    def disconnect(self):
        self.conectado = False


class SocketFalso:
    def __init__(self):
        self.cerrado = False

    def settimeout(self, timeout):
        pass

    def close(self):
        self.cerrado = True


class BrokerFalso:
    def __init__(self):
        self.clientes = []
        self.enviados = []
        self.estados = []
        self.falla_connect = False
        self.falla_publish = False
        self.durante_publish = None
        self.entrantes = []

    def cliente(self, *args, **kwargs):
        broker = self

        class Cliente:
            def __init__(self):
                self.sock = SocketFalso()

            def connect(self, **kwargs):
                if broker.falla_connect:
                    raise OSError("broker no disponible")

            def set_last_will(self, topico, dato, retain, qos):
                self.testamento = (topico, json.loads(dato), retain, qos)

            def set_callback(self, callback):
                self.callback = callback

            def subscribe(self, topico, qos):
                assert qos == 1
                self.suscripcion = topico

            def check_msg(self):
                if broker.entrantes:
                    self.callback(self.suscripcion, broker.entrantes.pop(0))

            def publish(self, topico, dato, qos, retain):
                assert qos == 1
                if broker.falla_publish:
                    raise OSError("publicacion sin confirmacion")
                if retain:
                    broker.estados.append((topico, json.loads(dato), retain, qos))
                    return
                if broker.durante_publish is not None:
                    broker.durante_publish(topico)
                broker.enviados.append((topico, json.loads(dato)))

        cliente = Cliente()
        self.clientes.append(cliente)
        return cliente


class PruebaRed(unittest.TestCase):
    def setUp(self):
        self.ms = 0
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.dict(sys.modules))
        self.stack.enter_context(patch.object(sys, "path", [str(FIRMWARE)] + sys.path))
        self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        reloj = types.ModuleType("time")
        reloj.ticks_ms = lambda: self.ms
        reloj.ticks_diff = lambda a, b: a - b
        for nombre in ("config", "mensajes", "red"):
            sys.modules.pop(nombre, None)
        sys.modules["time"] = reloj
        self.config = importlib.import_module("config")
        self.config.HABILITAR_ORDENES_MQTT = False
        self.red = importlib.import_module("red")
        self.wifi = WiFiFalso(True)
        self.broker = BrokerFalso()
        self.servicio = self.red.ServicioRed(self.wifi, self.broker.cliente,
                                            threading.Lock(), "prueba")

    def test_estado_retenido_y_testamento_al_reconectar(self):
        topico = self.servicio.topico_telemetria.rsplit(b"/", 1)[0] + b"/estado"
        estado = {"version": 2, "dispositivo": self.config.MQTT_DISPOSITIVO,
                  "sesion": "prueba"}
        self.servicio.paso()
        self.wifi.conectado = False
        self.servicio.paso()
        self.wifi.conectado = True
        self.servicio.paso()
        self.assertEqual([cliente.testamento for cliente in self.broker.clientes],
                         [(topico, dict(estado, estado="offline"), True, 1)] * 2)
        self.assertEqual(self.broker.estados,
                         [(topico, dict(estado, estado="online"), True, 1)] * 2)

    def test_json_tipos_y_sesion(self):
        self.servicio.encolar("HABITACION 1", "PRESENCIA", 95, True)
        self.servicio.paso()
        dato = self.broker.enviados[-1][1]
        self.assertEqual(dato, {
            "version": 1, "dispositivo": self.config.MQTT_DISPOSITIVO, "sesion": "prueba",
            "secuencia": 1, "tiempo_ms": 0, "zona": "HABITACION 1",
            "sensor": "HC-SR04", "evento": "PRESENCIA", "valor": 95, "luz": True})
        self.assertFalse(self.servicio.cola)

    def test_wifi_timeout_y_reintento_sin_perder_cola(self):
        self.wifi.conectado = False
        self.servicio.encolar("SALA", "PRESENCIA", "", True)
        self.servicio.paso()
        self.assertEqual(self.wifi.intentos, 1)
        self.ms = self.config.RED_WIFI_TIMEOUT_MS
        self.servicio.paso()
        self.servicio.paso()
        self.assertEqual(self.wifi.intentos, 1)
        self.ms += self.config.RED_REINTENTO_MS
        self.servicio.paso()
        self.assertEqual(self.wifi.intentos, 2)
        self.wifi.conectado = True
        self.servicio.paso()
        self.assertFalse(self.servicio.cola)

    def test_broker_caido_cierra_socket_y_recupera(self):
        self.broker.falla_connect = True
        self.servicio.encolar("SALA", "IRQ_PIR", 1, False)
        self.servicio.paso()
        self.assertTrue(self.broker.clientes[0].sock.cerrado)
        self.assertEqual(len(self.servicio.cola), 1)
        self.servicio.paso()
        self.assertEqual(len(self.broker.clientes), 1)
        self.ms += self.config.RED_REINTENTO_MS
        self.broker.falla_connect = False
        self.servicio.paso()
        self.assertEqual(self.broker.enviados[-1][1]["evento"], "IRQ_PIR")

    def test_publicacion_fallida_se_reenvia_en_orden(self):
        self.servicio.paso()
        self.broker.falla_publish = True
        self.servicio.encolar("SALA", "PRESENCIA", "", True)
        self.servicio.encolar("SALA", "LUZ_ENCENDIDA", "", True)
        self.servicio.paso()
        self.assertEqual(len(self.servicio.cola), 2)
        self.broker.falla_publish = False
        self.ms += self.config.RED_REINTENTO_MS
        self.servicio.paso()
        self.servicio.paso()
        datos = [d for _, d in self.broker.enviados if d["evento"] != "LATIDO"]
        self.assertEqual([d["secuencia"] for d in datos], [1, 2])

    def test_cola_limitada_y_descarte_durante_envio(self):
        self.config.RED_MAX_PENDIENTES = 2
        for i in range(3):
            self.servicio.encolar("SALA", "IRQ_PIR", i)
        self.assertEqual(self.servicio.descartados, 1)
        self.assertEqual([s for s, _ in self.servicio.cola], [2, 3])

        def producir(topico):
            if topico == self.servicio.topico_eventos:
                self.servicio.encolar("SALA", "IRQ_PIR", 4)

        self.broker.durante_publish = producir
        self.servicio.paso()
        self.assertEqual([s for s, _ in self.servicio.cola], [3, 4])

    def test_latido_y_perdida_wifi(self):
        self.servicio.paso()
        self.ms += self.config.RED_LATIDO_MS
        self.servicio.paso()
        self.assertEqual(len(self.broker.enviados), 2)
        self.assertEqual(self.broker.enviados[-1][1]["evento"], "LATIDO")
        self.wifi.conectado = False
        self.servicio.paso()
        self.assertTrue(self.broker.clientes[-1].sock.cerrado)

    def test_umqtt_antiguo_y_rechazo_del_broker(self):
        # Wokwi puede incluir una versión sin el argumento timeout en CONNECT.
        original = self.servicio.cliente_mqtt

        def antiguo(*args, **kwargs):
            cliente = original(*args, **kwargs)
            cliente.connect = lambda: None
            return cliente

        self.servicio.cliente_mqtt = antiguo
        self.servicio.paso()
        self.assertIsNotNone(self.servicio.cliente)

        class RechazoMQTT(Exception):
            pass

        def rechazar(*args, **kwargs):
            raise RechazoMQTT("CONNACK rechazado")

        self.servicio._cerrar()
        self.servicio.cliente_mqtt = rechazar
        self.servicio.paso()
        self.assertIsNone(self.servicio.cliente)
        self.assertIsNotNone(self.servicio.ultimo_fallo)

    def test_envio_bloqueado_no_retiene_candado_del_productor(self):
        # Mantener una publicación en espera y producir desde el otro hilo.
        # Los límites temporales solo previenen un test colgado si se rompe el candado.
        esperando = threading.Event()
        liberar = threading.Event()
        encolado = threading.Event()

        def bloquear(topico):
            if topico == self.servicio.topico_eventos:
                esperando.set()
                liberar.wait(2)

        self.servicio.encolar("SALA", "PRESENCIA", "", True)
        self.broker.durante_publish = bloquear
        consumidor = threading.Thread(target=self.servicio.paso)
        consumidor.start()
        try:
            self.assertTrue(esperando.wait(1))

            def producir():
                self.servicio.encolar("SALA", "LUZ_ENCENDIDA", "", True)
                encolado.set()

            productor = threading.Thread(target=producir)
            productor.start()
            try:
                self.assertTrue(encolado.wait(1))
            finally:
                liberar.set()
                productor.join(2)
        finally:
            liberar.set()
            consumidor.join(2)
        self.assertFalse(consumidor.is_alive())
        self.assertEqual([s for s, _ in self.servicio.cola], [2])

    def test_red_desactivada_no_importa_hardware(self):
        self.red.iniciar()
        self.assertIsNone(self.red._servicio)
        self.config.HABILITAR_RED = True
        self.config.MQTT_SERVIDOR = ""
        self.red.iniciar()
        self.assertIsNone(self.red._servicio)

    def test_config_real_sin_secrets_no_impide_control_local(self):
        # config no debe cargar secrets.py durante el arranque de los sensores.
        self.config.ENTORNO = "real"
        self.config.HABILITAR_RED = True
        self.config.MQTT_SERVIDOR = "broker-simulado.invalid"
        red_hilo = types.ModuleType("_thread")
        red_hilo.allocate_lock = threading.Lock
        red_hilo.start_new_thread = lambda *args: self.fail("No debe arrancar sin credenciales")
        network = types.ModuleType("network")
        network.STA_IF = 0
        network.WLAN = lambda _: self.wifi
        simple = types.ModuleType("umqtt.simple")
        simple.MQTTClient = self.broker.cliente
        sys.modules.update({"_thread": red_hilo, "network": network,
                            "umqtt": types.ModuleType("umqtt"), "umqtt.simple": simple,
                            "secrets": None})
        self.red.iniciar()
        self.assertIsNone(self.red._servicio)

    def test_hilo_se_inicia_una_sola_vez(self):
        red_hilo = types.ModuleType("_thread")
        iniciados = []
        red_hilo.allocate_lock = threading.Lock
        red_hilo.start_new_thread = lambda tarea, args: iniciados.append((tarea, args))
        network = types.ModuleType("network")
        network.STA_IF = 0
        network.WLAN = lambda _: self.wifi
        umqtt = types.ModuleType("umqtt")
        simple = types.ModuleType("umqtt.simple")
        simple.MQTTClient = self.broker.cliente
        sys.modules.update({"_thread": red_hilo, "network": network,
                            "umqtt": umqtt, "umqtt.simple": simple})
        self.config.HABILITAR_RED = True
        self.config.MQTT_SERVIDOR = "broker-simulado.invalid"
        self.red.iniciar()
        self.red.iniciar()
        self.assertEqual(len(iniciados), 1)
        self.assertIsNotNone(self.red._servicio)

    def test_telemetria_conserva_solo_la_ultima_muestra(self):
        self.ms = self.config.TELEMETRIA_INTERVALO_MS
        self.servicio.muestrear(False, 400, 1, False, False, False)
        primera = json.loads(self.servicio.instantanea)
        self.assertIsNone(primera["lecturas"]["distancia_cm"])
        self.ms += self.config.TELEMETRIA_INTERVALO_MS
        self.servicio.muestrear(True, 400, 60, True, True, False)
        self.servicio.paso()
        topico, mensaje = self.broker.enviados[-1]
        self.assertEqual(topico, self.servicio.topico_telemetria)
        self.assertEqual(mensaje["lecturas"], {"pir": 1, "ldr_adc": 400, "distancia_cm": 60})
        self.assertEqual(mensaje["secuencia"], primera["secuencia"] + 1)
        self.assertIsNone(self.servicio.instantanea)

    def test_orden_valida_invalida_y_reconexion(self):
        self.config.HABILITAR_ORDENES_MQTT = True
        self.broker.entrantes.extend([
            b'{"id":"1","zona":"SALA","accion":"apagar"}',
            b'{"id":"2","zona":"SALA","accion":"encender"}',
            b'{"id":"3","zona":"SALA","accion":"auto"}',
        ])
        self.servicio.paso()
        self.assertEqual(self.broker.clientes[0].suscripcion, self.servicio.topico_comandos)
        self.servicio.paso()
        self.assertEqual(self.servicio.tomar_orden(), "apagar")
        self.assertIsNone(self.servicio.tomar_orden())
        self.assertIn("Orden rechazada", sys.stdout.getvalue())
        self.wifi.conectado = False
        self.servicio.paso()
        self.wifi.conectado = True
        self.servicio.paso()
        self.assertEqual(self.broker.clientes[1].suscripcion, self.servicio.topico_comandos)
        self.assertEqual(self.servicio.tomar_orden(), "auto")

    def test_orden_apagar_en_ciclo_principal(self):
        fuente = (FIRMWARE / "main.py").read_text(encoding="utf-8")
        broker = BrokerFalso()
        broker.entrantes.append(b'{"id":"1","zona":"SALA","accion":"apagar"}')

        def preparar():
            import config
            import red
            config.HABILITAR_ORDENES_MQTT = True
            red._servicio = red.ServicioRed(WiFiFalso(True), broker.cliente,
                                           threading.Lock(), "integracion")
            return red._servicio

        salida, _ = ejecutar(fuente, "main.py", preparar_red=preparar)
        self.assertIn("[SALA] Orden MQTT aplicada: apagar", salida)
        self.assertIn("[SALA] Presencia detectada", salida)
        self.assertNotIn("[SALA] Luz ENCENDIDA", salida)
        self.assertIn("[HABITACION 1] Luz ENCENDIDA", salida)

    def test_main_sin_wifi_con_broker_caido_y_conectado(self):
        fuente = (FIRMWARE / "main.py").read_text(encoding="utf-8")
        base, ns_base = ejecutar(fuente, "main.py")
        esperados = ns_base["historial"].eventos()
        for modo in ("sin_wifi", "broker_caido", "conectado"):
            broker = BrokerFalso()
            broker.falla_connect = modo == "broker_caido"

            def preparar():
                import red
                servicio = red.ServicioRed(WiFiFalso(modo != "sin_wifi"),
                                           broker.cliente, threading.Lock(), "integracion")
                red._servicio = servicio
                return servicio

            salida, ns = ejecutar(fuente, "main.py", preparar_red=preparar)
            sin_red = "\n".join(l for l in salida.splitlines() if not l.startswith("[RED]"))
            self.assertEqual(sin_red, "\n".join(l for l in base.splitlines() if not l.startswith("[RED]")))
            self.assertEqual(ns["historial"].eventos(), esperados)
            self.assertEqual(ns["actuador_leds"]._estado, 0)
            if modo == "conectado":
                datos = [d for _, d in broker.enviados if d.get("evento") not in (None, "LATIDO")]
                muestras = [d for t, d in broker.enviados if t.endswith(b"/telemetria")]
                self.assertEqual(len(muestras), 7)
                self.assertTrue(all(m["version"] == 2 and m["intervalo_ms"] == 2000 for m in muestras))
                self.assertTrue(all({"pir", "ldr_adc"} <= m["lecturas"].keys() for m in muestras))
                self.assertEqual(muestras[-1]["luces"], {"SALA": False, "HABITACION_1": False, "HABITACION_2": False})
                self.assertEqual(len(datos), 16)
                self.assertEqual([d["evento"] for d in datos], [e[2] for e in esperados])
                self.assertEqual([d["tiempo_ms"] for d in datos], [e[0] for e in esperados])
            else:
                self.assertEqual(len(ns["red"]._servicio.cola), 16)


if __name__ == "__main__":
    unittest.main()
