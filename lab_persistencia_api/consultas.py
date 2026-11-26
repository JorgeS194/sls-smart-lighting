# Consultas sobre la base del proyecto. Uso: python consultas.py ultimos -n 5 | resumen | horas | csv --salida datos.csv
import argparse

import db

ap = argparse.ArgumentParser()
ap.add_argument("comando", choices=["ultimos", "resumen", "horas", "csv"])
ap.add_argument("-n", type=int, default=10)
ap.add_argument("--db", default=None)
ap.add_argument("--salida", default="datos.csv")
a = ap.parse_args()
con = db.conectar(a.db)

if a.comando == "ultimos":
    for f in db.ultimos(con, a.n):
        print(" ".join("%s=%s" % (k, f[k]) for k in f.keys() if k != "id"))
elif a.comando == "resumen":
    r = db.resumen(con)
    print(" ".join("%s=%s" % (k, r[k]) for k in r.keys()))
elif a.comando == "horas":
    for f in db.promedio_por_hora(con):
        print(f["hora"], "promedio=%s (%s registros)" % (f["promedio"], f["n"]))
else:
    print("Filas exportadas:", db.exportar_csv(con, a.salida), "->", a.salida)
