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

from .monitor import Monitor
from .persistencia import Persistencia
from .procesamiento import procesar
from .receptor import (SENSORES, objeto_json, validar_comando, validar_disponibilidad,
                       validar_instantanea, validar_mensaje)

LOG = logging.getLogger(__name__)


class Servicio:
    def __init__(self, directorio, silencio_s=6):
        self.persistencia = Persistencia(directorio)
        self.estado = self.persistencia.cargar()
        self.persistencia.snapshot(self.estado)
        self.lock = threading.RLock()
        self.monitor = Monitor(Path(directorio) / "eventos_comunicacion.csv", silencio_s)
        self.mqtt = None
        self.conectado = False
        self.topico_comandos = ""

    def recibir(self, payload):
        return self._guardar_lecturas([validar_mensaje(payload)])

    def recibir_mqtt(self, topico, payload, prefijo):
        if topico == prefijo + "/telemetria":
            return self.recibir(payload)
        partes = topico.split("/")
        if partes[:-2] != prefijo.split("/") or partes[-1] not in ("telemetria", "estado"):
            raise ValueError("Tópico MQTT inválido")
        dispositivo, tipo = partes[-2:]
        with self.lock:
            if tipo == "estado":
                sesion, estado = validar_disponibilidad(payload, dispositivo)
                self.monitor.disponibilidad(dispositivo, sesion, estado)
                return
            mensaje = objeto_json(payload)
            filas = validar_instantanea(mensaje, dispositivo)
            resultado = self._guardar_lecturas(filas)
            self.monitor.telemetria(dispositivo, mensaje["sesion"], mensaje["intervalo_ms"])
            return resultado

    def cambiar_conexion(self, conectado):
        with self.lock:
            if conectado:
                self.monitor.reiniciar_plazos()
            self.conectado = conectado

    def revisar_comunicacion(self):
        with self.lock:
            if self.conectado:
                self.monitor.revisar()

    def _guardar_lecturas(self, mensajes):
        with self.lock:
            nuevo = self.estado
            filas = []
            for mensaje in mensajes:
                nuevo, fila = procesar(nuevo, mensaje)
                filas.append(fila)
            try:
                self.persistencia.guardar_lote(nuevo, filas)
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


class Servidor(ThreadingHTTPServer):
    def __init__(self, direccion, handler, servicio):
        self.servicio = servicio
        super().__init__(direccion, handler)

    def service_actions(self):
        try:
            self.servicio.revisar_comunicacion()
        except OSError:
            LOG.exception("No se pudo registrar el cambio de comunicación")


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
        servicio.cambiar_conexion(reason_code == 0)
        if servicio.conectado:
            client.subscribe(args.prefijo + "/telemetria", qos=1)
            client.subscribe(args.prefijo + "/+/telemetria", qos=1)
            client.subscribe(args.prefijo + "/+/estado", qos=1)
        else:
            LOG.error("Broker rechazó conexión: %s", reason_code)

    def desconectado(client, userdata, flags, reason_code, properties):
        servicio.cambiar_conexion(False)

    def mensaje(client, userdata, msg):
        try:
            if len(msg.payload) > 16384:
                raise ValueError("Mensaje demasiado grande")
            servicio.recibir_mqtt(msg.topic, msg.payload, args.prefijo)
        except (ValueError, OSError):
            LOG.exception("Mensaje MQTT rechazado o no guardado")

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
    parser.add_argument("--silencio-s", type=int, default=6,
                        help="Segundos sin telemetría, mínimo 6 y tres intervalos del dispositivo")
    parser.add_argument("--origen", default="http://localhost:5173")
    args = parser.parse_args()
    if args.silencio_s < 6:
        parser.error("--silencio-s debe ser de al menos 6 segundos")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    servicio = Servicio(args.datos, args.silencio_s)
    servidor = Servidor((args.host, args.puerto), crear_handler(servicio, args.origen), servicio)
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
