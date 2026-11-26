# Capa de base de datos del SLS (Parte B, TODO 1 a 6).
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
    # TODO 1: nombre + tipo SQL, NOT NULL si es obligatorio y un CHECK con las reglas del campo.
    texto = n + " " + TIPOS_SQL[c["tipo"]]          # ej.: luz_adc INTEGER
    if c.get("obligatorio"):
        texto += " NOT NULL"                         # ej.: luz_adc INTEGER NOT NULL

    reglas = []                                      # cada regla es un pedacito del CHECK
    if "minimo" in c and "maximo" in c:
        reglas.append("%s BETWEEN %s AND %s" % (n, literal(c["minimo"]), literal(c["maximo"])))
    elif "minimo" in c:
        reglas.append("%s >= %s" % (n, literal(c["minimo"])))
    elif "maximo" in c:
        reglas.append("%s <= %s" % (n, literal(c["maximo"])))
    if "permitidos" in c:
        valores = ", ".join(literal(v) for v in c["permitidos"])
        reglas.append("%s IN (%s)" % (n, valores))

    if reglas:
        texto += " CHECK (" + " AND ".join(reglas) + ")"
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
    # TODO 2: INSERT con la fecha y todas las columnas. Los VALORES van con "?" (parametros);
    # la tabla y las columnas salen de proyecto.py (ya validado), nunca de un usuario.
    columnas = ["fecha"] + COLUMNAS
    marcas = ", ".join(["?"] * len(columnas))        # "?, ?, ?, ?, ?, ?"
    sql = "INSERT INTO %s (%s) VALUES (%s)" % (TABLA, ", ".join(columnas), marcas)
    valores = [ahora()] + [d.get(n) for n in COLUMNAS]   # d.get: un opcional ausente queda en NULL
    cursor = con.execute(sql, valores)
    con.commit()                                     # sin commit el dato no queda guardado
    return cursor.lastrowid                          # id de la fila nueva


def registrar_evento(con, tipo, detalle=""):
    con.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (ahora(), tipo, detalle))
    con.commit()


def ultimos(con, n=10):
    # TODO 3: los n registros mas recientes (id mayor = mas nuevo), el mas nuevo primero.
    sql = "SELECT * FROM %s ORDER BY id DESC LIMIT ?" % TABLA
    return con.execute(sql, (n,)).fetchall()


def promedio_por_hora(con):
    # TODO 4: una fila por hora. "2026-11-12T14:30:05Z" -> los 13 primeros caracteres = "2026-11-12T14".
    sql = ("SELECT substr(fecha, 1, 13) AS hora, ROUND(AVG(%s), 1) AS promedio, COUNT(*) AS n "
           "FROM %s GROUP BY hora ORDER BY hora" % (CAMPO_PRINCIPAL, TABLA))
    return con.execute(sql).fetchall()


def resumen(con):
    # TODO 5: una sola fila con las estadisticas de todo el historial.
    # Con la tabla vacia, COUNT da 0 y MIN/MAX/AVG dan NULL (None en Python), como pide el profe.
    sql = ("SELECT COUNT(*) AS total, MIN(%s) AS minimo, MAX(%s) AS maximo, ROUND(AVG(%s), 1) AS promedio "
           "FROM %s" % (CAMPO_PRINCIPAL, CAMPO_PRINCIPAL, CAMPO_PRINCIPAL, TABLA))
    return con.execute(sql).fetchone()


def exportar_csv(con, ruta):
    # TODO 6: CSV con encabezado (fecha + columnas) y todos los registros, del mas viejo al mas nuevo.
    sql = "SELECT fecha, %s FROM %s ORDER BY id" % (", ".join(COLUMNAS), TABLA)
    filas = con.execute(sql).fetchall()
    with open(ruta, "w", newline="", encoding="utf-8") as archivo:   # newline="" evita lineas en blanco en Windows
        escritor = csv.writer(archivo)
        escritor.writerow(["fecha"] + COLUMNAS)
        for fila in filas:
            escritor.writerow(tuple(fila))
    return len(filas)
