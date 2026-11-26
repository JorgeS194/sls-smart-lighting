# Completa los TODO 1 a 6.
import csv
import sqlite3
from datetime import datetime, timezone

import proyecto
from proyecto import CAMPOS, TABLA, CAMPO_PRINCIPAL

TIPOS_SQL = {"entero": "INTEGER", "real": "REAL", "texto": "TEXT"}
COLUMNAS = [c["nombre"] for c in CAMPOS]


def literal(v):
    """Valor fijo de proyecto.py (no de un usuario) escrito en una restriccion CHECK."""
    return repr(v) if isinstance(v, str) else str(v)


def definicion_columna(c):
    """Ej.: humedad INTEGER NOT NULL CHECK (humedad BETWEEN 0 AND 100)"""
    n = c["nombre"]
    # TODO 1: arma el texto de la columna: nombre, tipo SQL (TIPOS_SQL), NOT NULL si es obligatorio y
    #         las restricciones CHECK segun minimo, maximo (BETWEEN, >= o <=) y permitidos (IN (...)).
    #         Usa literal(v) para escribir los valores permitidos.
    texto = n + " " + TIPOS_SQL[c["tipo"]]
    if c.get("obligatorio"):
        texto += " NOT NULL"
    restricciones = []
    # Se pregunta con "in c" y no con c.get(): un minimo de 0 es falso en Python y se perderia.
    if "minimo" in c and "maximo" in c:
        restricciones.append("%s BETWEEN %s AND %s" % (n, literal(c["minimo"]), literal(c["maximo"])))
    elif "minimo" in c:
        restricciones.append("%s >= %s" % (n, literal(c["minimo"])))
    elif "maximo" in c:
        restricciones.append("%s <= %s" % (n, literal(c["maximo"])))
    if "permitidos" in c:
        restricciones.append("%s IN (%s)" % (n, ", ".join(literal(v) for v in c["permitidos"])))
    if restricciones:
        texto += " CHECK (" + " AND ".join(restricciones) + ")"
    return texto


def esquema():
    columnas = ["id INTEGER PRIMARY KEY AUTOINCREMENT", "fecha TEXT NOT NULL"]
    columnas += [definicion_columna(c) for c in CAMPOS]
    return ("CREATE TABLE IF NOT EXISTS %s (\n    %s\n);\n"
            "CREATE INDEX IF NOT EXISTS idx_%s_fecha ON %s (fecha);\n"
            "CREATE TABLE IF NOT EXISTS eventos (\n"
            "    id INTEGER PRIMARY KEY AUTOINCREMENT,\n    fecha TEXT NOT NULL,\n"
            "    tipo TEXT NOT NULL,\n    detalle TEXT\n);\n"
            % (TABLA, ",\n    ".join(columnas), TABLA, TABLA))


def ahora():
    """Fecha y hora UTC en formato ISO 8601 (ej. 2026-11-12T14:30:05Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def conectar(ruta=None):
    con = sqlite3.connect(ruta or proyecto.DB)
    con.row_factory = sqlite3.Row
    con.executescript(esquema())
    return con


def insertar(con, d):
    """Guarda un registro y devuelve su id."""
    # TODO 2: INSERT en TABLA con fecha (ahora()) y todas las COLUMNAS. Los VALORES van como parametros (?);
    #         los nombres de tabla y columna salen de proyecto.py (ya validados), nunca de un usuario.
    #         Usa d.get(n) para que un campo opcional ausente se guarde vacio. Confirma con commit y
    #         devuelve el id nuevo (cursor.lastrowid).
    return None


def registrar_evento(con, tipo, detalle=""):
    con.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (ahora(), tipo, detalle))
    con.commit()


def ultimos(con, n=10):
    # TODO 3: los ultimos n registros de TABLA, del mas reciente al mas antiguo (ORDER BY id DESC, LIMIT ?).
    return []


def promedio_por_hora(con):
    # TODO 4: columnas hora (los 13 primeros caracteres de fecha: substr(fecha, 1, 13)), promedio de CAMPO_PRINCIPAL
    #         (1 decimal) y n (cantidad), agrupadas por hora y ordenadas por hora.
    return []


def resumen(con):
    # TODO 5: una fila con total, minimo, maximo y promedio (1 decimal) de CAMPO_PRINCIPAL.
    #         Con la tabla vacia, total es 0 y los demas valores quedan vacios (None).
    return con.execute("SELECT 0 AS total, NULL AS minimo, NULL AS maximo, NULL AS promedio").fetchone()


def exportar_csv(con, ruta):
    # TODO 6: CSV con encabezado (fecha y las COLUMNAS) y todos los registros en orden de id.
    #         Devuelve la cantidad de filas escritas.
    return 0
