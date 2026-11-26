# Autoprueba de la Parte A y B (proyecto.py + db.py). Uso: python probar_parte_b.py
# Usa una base en memoria: no crea ni toca proyecto.db. Sirve de evidencia para el informe.
import os
import sqlite3
import tempfile

import db
import proyecto

buenos = total = 0


def prueba(nombre, condicion):
    global buenos, total
    total += 1
    buenos += bool(condicion)
    print(("OK    " if condicion else "FALLA ") + nombre)


print("=== Esquema generado desde la ficha ===")
print(db.esquema())

con = db.conectar(":memory:")
prueba("conectar(':memory:') crea las tablas sin errores", True)

# La base misma rechaza datos imposibles (CHECK) aunque se salte la validacion de Python.
casos_malos = [
    ("luz_adc = 99999 (maximo 4095)", dict(proyecto.EJEMPLO, luz_adc=99999)),
    ("luz_adc = -1 (minimo 0)", dict(proyecto.EJEMPLO, luz_adc=-1)),
    ("distancia_cm = 999 (maximo 400)", dict(proyecto.EJEMPLO, distancia_cm=999)),
    ("movimiento = 5 (solo 0 o 1)", dict(proyecto.EJEMPLO, movimiento=5)),
    ("zona = None (obligatoria)", dict(proyecto.EJEMPLO, zona=None)),
]
for nombre, cuerpo in casos_malos:
    try:
        db.insertar(con, cuerpo)
        prueba("la base rechaza " + nombre, False)
    except sqlite3.IntegrityError as e:
        print("      mensaje de la base:", e)
        prueba("la base rechaza " + nombre, True)

prueba("tabla vacia: resumen con total 0 y resto None",
       tuple(db.resumen(con)) == (0, None, None, None))
prueba("tabla vacia: ultimos devuelve lista vacia", db.ultimos(con, 5) == [])

id1 = db.insertar(con, proyecto.EJEMPLO)
id2 = db.insertar(con, dict(proyecto.EJEMPLO, luz_adc=2151))
sin_distancia = {k: v for k, v in proyecto.EJEMPLO.items() if k != "distancia_cm"}
id3 = db.insertar(con, dict(sin_distancia, luz_adc=2152))
prueba("insertar devuelve ids 1, 2, 3", (id1, id2, id3) == (1, 2, 3))
prueba("campo opcional ausente se guarda vacio (NULL)", db.ultimos(con, 1)[0]["distancia_cm"] is None)

u = db.ultimos(con, 2)
prueba("ultimos(2): el mas reciente primero", [f["luz_adc"] for f in u] == [2152, 2151])

r = db.resumen(con)
prueba("resumen: total 3, minimo 2150, maximo 2152, promedio 2151.0",
       (r["total"], r["minimo"], r["maximo"], r["promedio"]) == (3, 2150, 2152, 2151.0))

h = db.promedio_por_hora(con)
prueba("promedio_por_hora: una hora con 3 registros", len(h) == 1 and h[0]["n"] == 3 and len(h[0]["hora"]) == 13)

inyeccion = "x'); DROP TABLE %s; --" % proyecto.TABLA
db.insertar(con, dict(proyecto.EJEMPLO, zona=inyeccion))
prueba("inyeccion SQL: se guarda como texto y la tabla sigue viva",
       db.resumen(con)["total"] == 4 and db.ultimos(con, 1)[0]["zona"] == inyeccion)

ruta = os.path.join(tempfile.gettempdir(), "prueba_sls.csv")
n = db.exportar_csv(con, ruta)
with open(ruta, encoding="utf-8") as f:
    lineas = f.read().splitlines()
prueba("exportar_csv: devuelve 4 y el archivo tiene encabezado + 4 filas", n == 4 and len(lineas) == 5)
prueba("exportar_csv: encabezado correcto", lineas[0] == "fecha," + ",".join(db.COLUMNAS))
os.remove(ruta)

print("\nResultado: %d de %d comprobaciones" % (buenos, total))
