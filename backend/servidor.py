"""Servidor local del dashboard. Ejecutar: python backend/servidor.py."""
import argparse
import csv
import io
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from estado import Almacen

RAIZ = Path(__file__).resolve().parents[1]


class Servidor(ThreadingHTTPServer):
    daemon_threads = True


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(RAIZ / "dashboard"), **kwargs)

    def enviar(self, dato, estado=200, tipo="application/json; charset=utf-8"):
        contenido = json.dumps(dato, ensure_ascii=False).encode() if not isinstance(dato, bytes) else dato
        self.send_response(estado)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(contenido)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(contenido)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; img-src 'self' data:; script-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()

    def do_GET(self):
        ruta = urlsplit(self.path).path
        if ruta == "/api/estado":
            self.enviar(dict(self.server.almacen.estado(), mqtt=self.server.mqtt_estado))
        elif ruta == "/api/exportar.csv":
            salida = io.StringIO(newline="")
            campos = ["recibido", "dispositivo", "sesion", "secuencia", "tiempo_ms",
                      "zona", "sensor", "evento", "valor", "luz"]
            escritor = csv.DictWriter(salida, fieldnames=campos, extrasaction="ignore")
            escritor.writeheader()
            for fila in self.server.almacen.eventos(100000):
                # Impedir fórmulas al abrir texto recibido en una hoja de cálculo.
                escritor.writerow({k: "'" + v if isinstance(v, str) and v.startswith(("=", "+", "-", "@")) else v
                                   for k, v in fila.items()})
            self.enviar(salida.getvalue().encode("utf-8-sig"), tipo="text/csv; charset=utf-8")
        elif ruta.startswith("/api/"):
            self.enviar({"error": "Ruta inexistente"}, 404)
        elif ruta in ("/", "/index.html", "/styles.css", "/app.mjs", "/model.mjs", "/icon.svg"):
            super().do_GET()
        else:
            self.enviar({"error": "Archivo no disponible"}, 404)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/eventos":
            self.enviar({"error": "Ruta inexistente"}, 404)
            return
        origen = self.headers.get("Origin")
        if origen and origen != "http://" + self.headers.get("Host", ""):
            self.enviar({"error": "Origen no permitido"}, 403)
            return
        if self.headers.get_content_type() != "application/json":
            self.enviar({"error": "Se requiere application/json"}, 415)
            return
        try:
            longitud = int(self.headers.get("Content-Length", 0))
            if not 0 < longitud <= 512000:
                raise ValueError("El archivo supera el límite o está vacío")
            dato = json.loads(self.rfile.read(longitud))
            cantidad = self.server.almacen.agregar(dato if isinstance(dato, list) else [dato])
            self.enviar({"agregados": cantidad})
        except (ValueError, UnicodeError) as error:
            self.enviar({"error": str(error)}, 400)


def crear_servidor(puerto=8000, datos=None):
    carpeta = Path(datos) if datos is not None else RAIZ / "backend" / "datos"
    carpeta.mkdir(parents=True, exist_ok=True)
    servidor = Servidor(("127.0.0.1", puerto), Handler)
    servidor.almacen = Almacen(carpeta / "sls.sqlite3")
    servidor.mqtt_estado = {"configurado": False, "conectado": False, "error": None}
    return servidor


def main():
    parser = argparse.ArgumentParser(description="SLS · dashboard local")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--datos", default=None, help="Carpeta de datos alternativa, útil para pruebas")
    parser.add_argument("--mqtt-host", default="", help="Sin valor: no establece conexiones externas")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--topic", default="utp-sls/jorge-s194/casa-01/eventos")
    args = parser.parse_args()
    servidor = crear_servidor(args.port, args.datos)
    cliente = None
    try:
        if args.mqtt_host:
            from mqtt_receptor import conectar
            cliente = conectar(args.mqtt_host, args.mqtt_port, args.topic,
                                servidor.almacen, servidor.mqtt_estado)
        print("SLS Dashboard: http://127.0.0.1:{}".format(servidor.server_port), flush=True)
        print("Modo local. Ctrl+C para detener.", flush=True)
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if cliente is not None:
            cliente.disconnect()
            cliente.loop_stop()
        servidor.server_close()
        servidor.almacen.cerrar()


if __name__ == "__main__":
    main()
