# API REST del proyecto. Completa los TODO 9 a 14. Uso: python api.py (puerto 5000). Clave de escritura: variable de entorno API_KEY
import os
import sqlite3

from flask import Flask, g, jsonify, request, Response

import db
import proyecto
from validacion import validar

API_KEY = os.environ.get("API_KEY", "clave-curso")
HTML = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.html"), encoding="utf-8").read()

app = Flask(__name__)


def conexion():
    """Una conexion por peticion (SQLite no se comparte entre hilos)."""
    if "con" not in g:
        g.con = db.conectar(os.environ.get("PROYECTO_DB"))
    return g.con


@app.teardown_appcontext
def cerrar(_exc):
    con = g.pop("con", None)
    if con is not None:
        con.close()


def fila_a_dict(f):
    return {k: f[k] for k in f.keys()}


def clave_valida():
    # TODO 9: verdadero solo si el encabezado X-API-Key de la peticion es igual a API_KEY.
    return False


@app.get("/salud")
def salud():
    return jsonify(estado="ok", registros=db.resumen(conexion())["total"])


@app.get("/proyecto")
def ver_proyecto():
    return jsonify(nombre=proyecto.NOMBRE, principal=proyecto.CAMPO_PRINCIPAL,
                   campos=[c["nombre"] for c in proyecto.CAMPOS])


@app.post("/registros")
def crear_registro():
    # TODO 10: sin clave valida -> 401 {"error": "clave de API invalida"}. Lee el JSON con
    #          request.get_json(silent=True), valida con validar (400 con el motivo), guarda con db.insertar
    #          (500 si falla sqlite3) y responde 201 con {"id": id_nuevo}.
    return jsonify(error="pendiente"), 501


@app.get("/registros")
def listar_registros():
    # TODO 11: lee n de la direccion (10 por defecto). Si no es entero o no esta entre 1 y 100 -> 400 con el motivo.
    #          Si es valido devuelve la lista (usa fila_a_dict para convertir cada fila).
    return jsonify(error="pendiente"), 501


@app.get("/registros/ultimo")
def ultimo_registro():
    # TODO 12: el registro mas reciente; si no hay ninguno -> 404 {"error": "no hay registros"}.
    return jsonify(error="pendiente"), 501


@app.get("/resumen")
def ver_resumen():
    # TODO 13: devuelve el resumen como un objeto JSON.
    return jsonify(error="pendiente"), 501


@app.get("/horas")
def ver_horas():
    # TODO 14: devuelve el promedio por hora como una lista JSON.
    return jsonify(error="pendiente"), 501


@app.get("/")
def panel():
    return Response(HTML, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
