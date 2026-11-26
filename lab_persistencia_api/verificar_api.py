# Uso: python verificar_api.py --url http://127.0.0.1:5000 --clave clave-curso
# Ejecutala con la API encendida y con la base de datos VACIA (borra el archivo .db antes de empezar).
import argparse

import requests

import proyecto

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:5000")
ap.add_argument("--clave", default="clave-curso")
a = ap.parse_args()
U, H = a.url, {"X-API-Key": a.clave}
buenos = total = 0


def prueba(nombre, condicion):
    global buenos, total
    total += 1
    buenos += bool(condicion)
    print(("OK    " if condicion else "FALLA ") + nombre)


def seguro(f):
    try:
        return f()
    except Exception:
        return None


def codigo(r):
    return getattr(r, "status_code", None)


def post(cuerpo, headers=H):
    return seguro(lambda: requests.post(U + "/registros", json=cuerpo, headers=headers, timeout=5))


def get(ruta):
    return seguro(lambda: requests.get(U + ruta, timeout=5))


CAMPOS = {c["nombre"]: c for c in proyecto.CAMPOS}
P = proyecto.CAMPO_PRINCIPAL
E = proyecto.EJEMPLO
cp = CAMPOS[P]
p1 = E[P]
p2 = p1 + 1 if ("maximo" not in cp or p1 + 1 <= cp["maximo"]) else p1 - 1
if cp["tipo"] == "real":
    p2 = round(p2, 1)

prueba("ultimo sin datos responde 404", codigo(get("/registros/ultimo")) == 404)
prueba("POST sin clave responde 401", codigo(post(E, headers={})) == 401)
r = post(E)
prueba("POST valido responde 201 con id", codigo(r) == 201 and "id" in r.json())
malos = [("no es objeto", [1, 2])]
for n, c in CAMPOS.items():
    if c.get("obligatorio"):
        malos.append(("falta " + n, {k: v for k, v in E.items() if k != n}))
        break
if "maximo" in cp:
    malos.append(("%s sobre el maximo" % P, dict(E, **{P: cp["maximo"] + 1})))
if "minimo" in cp:
    malos.append(("%s bajo el minimo" % P, dict(E, **{P: cp["minimo"] - 1})))
malos.append(("%s con texto" % P, dict(E, **{P: "abc"})))
for n, c in CAMPOS.items():
    if "permitidos" in c and n != P:
        malos.append(("%s fuera de los permitidos" % n, dict(E, **{n: "zzz-invalido"})))
        break
codigos = [codigo(post(b)) for _, b in malos]
prueba("%d cuerpos invalidos responden 400 (%s)" % (len(malos), "; ".join(n for n, _ in malos)),
       codigos == [400] * len(malos))
r = seguro(lambda: requests.post(U + "/registros", data="hola", headers=dict(H, **{"Content-Type": "application/json"}), timeout=5))
prueba("JSON ilegible responde 400", codigo(r) == 400)
post(dict(E, **{P: p2}))
r = get("/registros?n=2")
prueba("lista n=2: mas reciente primero", codigo(r) == 200 and [x[P] for x in r.json()] == [p2, p1])
cods = [codigo(get("/registros?n=" + q)) for q in ("0", "101", "abc")]
prueba("n=0, n=101 y n=abc responden 400", cods == [400] * 3)
r = get("/registros/ultimo")
prueba("ultimo devuelve el mas reciente", codigo(r) == 200 and r.json().get(P) == p2)
r = get("/resumen")
j = r.json() if codigo(r) == 200 else {}
prueba("resumen: total 2, minimo y maximo correctos",
       j.get("total") == 2 and j.get("minimo") == min(p1, p2) and j.get("maximo") == max(p1, p2))
r = get("/horas")
j = r.json() if codigo(r) == 200 else []
prueba("horas: una hora con 2 registros", isinstance(j, list) and len(j) == 1 and j[0].get("n") == 2)
texto = next((n for n, c in CAMPOS.items() if c["tipo"] == "texto" and "permitidos" not in c), None)
if texto:
    r = post(dict(E, **{texto: "x'); DROP TABLE %s; --" % proyecto.TABLA}))
    r2 = get("/resumen")
    prueba("texto de inyeccion SQL en %s no rompe la tabla" % texto, codigo(r) == 201 and codigo(r2) == 200 and r2.json().get("total") == 3)
else:
    print("(sin campo de texto libre: se omite la prueba de inyeccion SQL)")
print("\nResultado: %d de %d comprobaciones" % (buenos, total))
