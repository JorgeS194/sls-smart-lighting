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
    nombres = ", ".join(COLUMNAS)
    marcas = ", ".join(["?"] * (len(COLUMNAS) + 1))   # una por columna, mas la fecha
    valores = [ahora()] + [d.get(n) for n in COLUMNAS]
    cursor = con.execute("INSERT INTO %s (fecha, %s) VALUES (%s)" % (TABLA, nombres, marcas), valores)
    con.commit()
    return cursor.lastrowid


def registrar_evento(con, tipo, detalle=""):
    con.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (ahora(), tipo, detalle))
    con.commit()


def ultimos(con, n=10):
    # TODO 3: los ultimos n registros de TABLA, del mas reciente al mas antiguo (ORDER BY id DESC, LIMIT ?).
    return con.execute("SELECT * FROM %s ORDER BY id DESC LIMIT ?" % TABLA, (n,)).fetchall()


def promedio_por_hora(con):
    # TODO 4: columnas hora (los 13 primeros caracteres de fecha: substr(fecha, 1, 13)), promedio de CAMPO_PRINCIPAL
    #         (1 decimal) y n (cantidad), agrupadas por hora y ordenadas por hora.
    return con.execute(
        "SELECT substr(fecha, 1, 13) AS hora, ROUND(AVG(%s), 1) AS promedio, COUNT(*) AS n "
        "FROM %s GROUP BY hora ORDER BY hora" % (CAMPO_PRINCIPAL, TABLA)).fetchall()


def resumen(con):
    # TODO 5: una fila con total, minimo, maximo y promedio (1 decimal) de CAMPO_PRINCIPAL.
    #         Con la tabla vacia, total es 0 y los demas valores quedan vacios (None).
    # Con la tabla vacia, MIN, MAX y AVG devuelven NULL (None en Python) y COUNT devuelve 0.
    return con.execute(
        "SELECT COUNT(*) AS total, MIN(%s) AS minimo, MAX(%s) AS maximo, ROUND(AVG(%s), 1) AS promedio "
        "FROM %s" % (CAMPO_PRINCIPAL, CAMPO_PRINCIPAL, CAMPO_PRINCIPAL, TABLA)).fetchone()


def exportar_csv(con, ruta):
    # TODO 6: CSV con encabezado (fecha y las COLUMNAS) y todos los registros en orden de id.
    #         Devuelve la cantidad de filas escritas.
    filas = con.execute("SELECT fecha, %s FROM %s ORDER BY id" % (", ".join(COLUMNAS), TABLA)).fetchall()
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["fecha"] + COLUMNAS)
        for fila in filas:
            escritor.writerow(list(fila))   # un None sale como celda vacia
    return len(filas)
