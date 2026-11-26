# Ingestor MQTT -> SQLite. Completa el TODO 8. Uso: python ingestor.py --grupo g1 --broker IP --usuario g1 --clave XXXX
import argparse
import json
import sqlite3

import paho.mqtt.client as mqtt

import db
import proyecto
from validacion import validar

ap = argparse.ArgumentParser()
ap.add_argument("--grupo", default="g1", help="usuario/grupo; los temas son utp/ds8/<grupo>/<TEMA>/...")
ap.add_argument("--broker", default="127.0.0.1")
ap.add_argument("--puerto", type=int, default=1883)
ap.add_argument("--usuario", default=None)
ap.add_argument("--clave", default=None)
ap.add_argument("--db", default=None)
args = ap.parse_args()

BASE = "utp/ds8/%s/%s" % (args.grupo, proyecto.TEMA)
T_DATOS = BASE + "/" + proyecto.TEMA_DATOS
T_ESTADO = BASE + "/estado"
con = db.conectar(args.db)
guardados = 0


def al_conectar(cliente, datos, banderas, codigo, propiedades=None):
    if codigo == 0:
        cliente.subscribe([(T_DATOS, 0), (T_ESTADO, 0)])
        print("Conectado al broker; escuchando", BASE)
    else:
        print("El broker rechazo la conexion (%s): revisa --usuario y --clave" % codigo)


def al_mensaje(cliente, datos, mensaje):
    global guardados
    texto = mensaje.payload.decode(errors="replace")
    # TODO 8: segun el tema (mensaje.topic):
    #   - T_ESTADO: guarda un evento con db.registrar_evento(con, "ESTADO", texto).
    #   - T_DATOS: convierte el JSON (si falla, guarda el evento DATO_RECHAZADO y termina); valida con validar(d)
    #     (si hay problema, guarda DATO_RECHAZADO con el motivo y termina); si es valido, db.insertar(con, d)
    #     y suma a guardados.
    #   Captura sqlite3.Error para que el ingestor nunca se detenga. Imprime una linea por cada caso.
    try:
        if mensaje.topic == T_ESTADO:
            db.registrar_evento(con, "ESTADO", texto)
            print("Estado del dispositivo:", texto)
        elif mensaje.topic == T_DATOS:
            try:
                d = json.loads(texto)
            except (ValueError, RecursionError):
                # RecursionError: un JSON anidado miles de veces; no debe tumbar el ingestor.
                db.registrar_evento(con, "DATO_RECHAZADO", "no es JSON: " + texto[:80])
                print("Rechazado (no es JSON):", texto[:60])
                return
            problema = validar(d)
            if problema:
                db.registrar_evento(con, "DATO_RECHAZADO", problema)
                print("Rechazado:", problema)
                return
            nuevo_id = db.insertar(con, d)
            guardados += 1
            print("Guardado el registro", nuevo_id)
        else:
            print("Mensaje en otro tema, se ignora:", mensaje.topic)
    except sqlite3.Error as e:
        # Una falla de la base no debe detener la escucha: un error dentro del callback
        # haria terminar loop_forever.
        print("Error de la base de datos; el ingestor sigue:", e)


cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ingestor-" + args.grupo)
if args.usuario:
    cliente.username_pw_set(args.usuario, args.clave)
cliente.on_connect = al_conectar
cliente.on_message = al_mensaje
try:
    cliente.connect(args.broker, args.puerto)
except OSError as e:
    raise SystemExit("No llego al broker %s:%d (%s)" % (args.broker, args.puerto, e))
try:
    cliente.loop_forever()
except KeyboardInterrupt:
    print("Fin. Registros guardados en esta sesion:", guardados)
