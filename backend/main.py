"""Ejecutar desde la raíz: python -m backend.main --sin-mqtt."""
import argparse
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from .persistencia import Persistencia
from .procesamiento import procesar
from .receptor import SENSORES, validar_comando, validar_mensaje

LOG = logging.getLogger(__name__)


class Servicio:
    def __init__(self, directorio):
        self.persistencia = Persistencia(directorio)
        self.estado = self.persistencia.cargar()
        self.persistencia.snapshot(self.estado)
        self.lock = threading.RLock()
        self.mqtt = None
        self.conectado = False
        self.topico_comandos = ""

    def recibir(self, payload):
        mensaje = validar_mensaje(payload)
        with self.lock:
            nuevo, fila = procesar(self.estado, mensaje)
            try:
                self.persistencia.guardar(nuevo, fila)
            except OSError:
                # Reflejar cualquier fila ya confirmada aunque falle el snapshot.
                self.estado = self.persistencia.cargar()
                raise
            self.estado = nuevo
            return deepcopy(nuevo)

    def comando(self, mensaje):
        comando = validar_comando(mensaje)
        if not self.mqtt or not self.conectado:
            raise ConnectionError("MQTT desconectado; comando no enviado")
        comando["id"] = str(uuid4())
        resultado = self.mqtt.publish(self.topico_comandos, json.dumps(comando), qos=1, retain=False)
        if resultado.rc != 0:
            raise ConnectionError("No se pudo publicar el comando")
        return {"estado": "enviado_al_broker", "comando": comando}


def crear_handler(servicio, origen):
    class Handler(BaseHTTPRequestHandler):
        def responder(self, codigo, contenido):
            datos = json.dumps(contenido, ensure_ascii=False, allow_nan=False).encode("utf-8")
            self.send_response(codigo)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(datos)))
            self.send_header("Access-Control-Allow-Origin", origen)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(datos)

        def do_OPTIONS(self):
            self.responder(200, {})

        def do_GET(self):
            ruta = urlsplit(self.path)
            try:
                with servicio.lock:
                    if ruta.path == "/api/salud":
                        datos = {"estado": "ok", "mqtt_conectado": servicio.conectado}
                    elif ruta.path == "/api/estado":
                        datos = deepcopy(servicio.estado)
                    elif ruta.path == "/api/historial":
                        parametros = parse_qs(ruta.query)
                        limite = int(parametros.get("limite", ["100"])[0])
                        zona = parametros.get("zona", [None])[0]
                        if not 1 <= limite <= 1000 or (zona is not None and zona not in SENSORES):
                            raise ValueError("limite debe estar entre 1 y 1000; zona debe ser válida")
                        datos = {"historial": servicio.persistencia.historial(limite, zona)}
                    else:
                        self.responder(404, {"error": "Ruta no encontrada"})
                        return
                self.responder(200, datos)
            except ValueError as exc:
                self.responder(400, {"error": str(exc)})
            except OSError:
                LOG.exception("Error de almacenamiento")
                self.responder(500, {"error": "No se pudo leer el historial"})

        def do_POST(self):
            ruta = urlsplit(self.path).path
            if ruta not in ("/api/lecturas", "/api/comandos"):
                self.responder(404, {"error": "Ruta no encontrada"})
                return
            try:
                longitud = int(self.headers.get("Content-Length", "0"))
                if not 0 < longitud <= 16384:
                    self.responder(413, {"error": "Cuerpo requerido; máximo 16384 bytes"})
                    return
                self.connection.settimeout(5)
                mensaje = json.loads(self.rfile.read(longitud))
                if ruta == "/api/lecturas":
                    self.responder(201, servicio.recibir(mensaje))
                else:
                    self.responder(202, servicio.comando(mensaje))
            except (ValueError, UnicodeError) as exc:
                self.responder(400, {"error": str(exc)})
            except ConnectionError as exc:
                self.responder(503, {"error": str(exc)})
            except OSError:
                LOG.exception("Error al procesar solicitud")
                self.responder(500, {"error": "No se pudo completar la operación"})

    return Handler


def conectar_mqtt(servicio, args):
    import paho.mqtt.client as mqtt

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="sls-backend-" + uuid4().hex[:12])
    servicio.mqtt = cliente
    servicio.topico_comandos = args.prefijo + "/comandos"
    usuario = os.getenv("SLS_MQTT_USUARIO")
    if usuario:
        cliente.username_pw_set(usuario, os.getenv("SLS_MQTT_PASSWORD"))
    if args.tls:
        cliente.tls_set()

    def conectado(client, userdata, flags, reason_code, properties):
        servicio.conectado = reason_code == 0
        if servicio.conectado:
            client.subscribe(args.prefijo + "/telemetria", qos=1)
        else:
            LOG.error("Broker rechazó conexión: %s", reason_code)

    def desconectado(client, userdata, flags, reason_code, properties):
        servicio.conectado = False

    def mensaje(client, userdata, msg):
        try:
            if len(msg.payload) > 16384:
                raise ValueError("Mensaje demasiado grande")
            servicio.recibir(msg.payload)
        except (ValueError, OSError):
            LOG.exception("Telemetría rechazada o no guardada")

    cliente.on_connect = conectado
    cliente.on_disconnect = desconectado
    cliente.on_message = mensaje
    cliente.reconnect_delay_set(min_delay=1, max_delay=30)
    cliente.connect_async(args.broker, args.puerto_mqtt, keepalive=60)
    cliente.loop_start()
    return cliente


def main():
    parser = argparse.ArgumentParser(description="Backend SLS: MQTT y API para dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--puerto", type=int, default=8000)
    parser.add_argument("--datos", type=Path, default=Path(__file__).parent / "datos")
    parser.add_argument("--sin-mqtt", action="store_true")
    parser.add_argument("--broker", default=os.getenv("SLS_MQTT_HOST", "localhost"))
    parser.add_argument("--puerto-mqtt", type=int, default=1883)
    parser.add_argument("--prefijo", default=os.getenv("SLS_MQTT_PREFIJO", "utp-sls-g1"))
    parser.add_argument("--tls", action="store_true")
    parser.add_argument("--origen", default="http://localhost:5173")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    servicio = Servicio(args.datos)
    servidor = ThreadingHTTPServer((args.host, args.puerto), crear_handler(servicio, args.origen))
    cliente = None
    try:
        if not args.sin_mqtt:
            cliente = conectar_mqtt(servicio, args)
        LOG.info("API disponible en http://%s:%s/api/estado", args.host, args.puerto)
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
        if cliente:
            cliente.disconnect()
            cliente.loop_stop()


if __name__ == "__main__":
    main()
