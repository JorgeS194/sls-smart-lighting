# Publicador MQTT de prueba: reemplaza a mosquitto_pub para las Partes C, D e I.
# El broker, el usuario y la clave se reciben SOLO como argumentos: no se leen ni se guardan en archivos.
# El tema se arma con proyecto.py, igual que el ingestor, para que los dos siempre coincidan.
#
# Uso (--grupo es tu usuario; los temas son utp/ds8/<grupo>/<TEMA>/...):
#   python publicar_prueba.py --grupo g1 --broker IP --usuario g1 --clave XXXX datos
#   python publicar_prueba.py ... datos --cambiar ldr_adc=5000          (cambia un campo del EJEMPLO)
#   python publicar_prueba.py ... datos --quitar dispositivo            (quita un campo del EJEMPLO)
#   python publicar_prueba.py ... datos --cambiar distancia_cm=NaN      (json.loads acepta NaN e Infinity)
#   python publicar_prueba.py ... datos --crudo hola                    (texto que no es JSON)
#   python publicar_prueba.py ... estado offline
import argparse
import json
import threading

import paho.mqtt.client as mqtt

import proyecto


def valor(texto):
    """Entiende numeros, true/false/null, textos entre comillas, NaN e Infinity; si no es JSON, es texto."""
    try:
        return json.loads(texto)
    except ValueError:
        return texto


def armar_datos(cambiar, quitar, crudo):
    """Devuelve el texto exacto que se publicara en el tema de datos."""
    if crudo is not None:
        return crudo
    d = dict(proyecto.EJEMPLO)
    for par in cambiar:
        nombre, igual, texto = par.partition("=")
        if not igual or not nombre:
            raise SystemExit("--cambiar espera campo=valor, y recibi %r" % par)
        d[nombre] = valor(texto)
    for nombre in quitar:
        d.pop(nombre, None)
    return json.dumps(d)          # NaN e Infinity salen como NaN e Infinity, igual que en un mensaje real


def temas(grupo):
    base = "utp/ds8/%s/%s" % (grupo, proyecto.TEMA)
    return base + "/" + proyecto.TEMA_DATOS, base + "/estado"


def publicar(args, tema, mensaje):
    conectado = threading.Event()
    resultado = {}

    def al_conectar(cliente, datos, banderas, codigo, propiedades=None):
        resultado["codigo"] = codigo
        conectado.set()

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="publicador-" + args.grupo)
    if args.usuario:
        cliente.username_pw_set(args.usuario, args.clave)
    cliente.on_connect = al_conectar
    try:
        cliente.connect(args.broker, args.puerto)
    except OSError as e:
        raise SystemExit("No llego al broker %s:%d (%s)" % (args.broker, args.puerto, e))
    cliente.loop_start()
    try:
        if not conectado.wait(5):
            raise SystemExit("El broker no respondio en 5 segundos")
        if resultado["codigo"] != 0:
            raise SystemExit("El broker rechazo la conexion (%s): revisa --usuario y --clave" % resultado["codigo"])
        envio = cliente.publish(tema, mensaje, qos=1)
        envio.wait_for_publish(timeout=5)
        if not envio.is_published():
            raise SystemExit("El broker no confirmo la publicacion en 5 segundos")
    finally:
        cliente.loop_stop()
        cliente.disconnect()
    print("Publicado en", tema)
    print("Mensaje    :", mensaje)


def main():
    ap = argparse.ArgumentParser(description="Publica un mensaje de prueba en el broker MQTT.")
    ap.add_argument("--grupo", default="g1", help="usuario/grupo; los temas son utp/ds8/<grupo>/<TEMA>/...")
    ap.add_argument("--broker", default="127.0.0.1")
    ap.add_argument("--puerto", type=int, default=1883)
    ap.add_argument("--usuario", default=None)
    ap.add_argument("--clave", default=None)
    sub = ap.add_subparsers(dest="tipo", required=True)
    d = sub.add_parser("datos", help="publica en .../telemetria (por defecto, el EJEMPLO de proyecto.py)")
    d.add_argument("--cambiar", action="append", default=[], metavar="CAMPO=VALOR",
                   help="cambia un campo del EJEMPLO (se puede repetir)")
    d.add_argument("--quitar", action="append", default=[], metavar="CAMPO",
                   help="quita un campo del EJEMPLO (se puede repetir)")
    d.add_argument("--crudo", default=None, metavar="TEXTO", help="publica este texto tal cual, sin armar el JSON")
    e = sub.add_parser("estado", help="publica en .../estado")
    e.add_argument("texto", choices=["online", "offline"])
    args = ap.parse_args()

    t_datos, t_estado = temas(args.grupo)
    if args.tipo == "datos":
        publicar(args, t_datos, armar_datos(args.cambiar, args.quitar, args.crudo))
    else:
        publicar(args, t_estado, args.texto)


if __name__ == "__main__":
    main()
