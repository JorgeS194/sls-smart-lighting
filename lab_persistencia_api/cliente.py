# Cliente de prueba: envia registros de ejemplo a la API. Uso: python cliente.py --cantidad 10 --pausa 1
import argparse
import random
import time

import requests

import proyecto

ap = argparse.ArgumentParser()
ap.add_argument("--url", default="http://127.0.0.1:5000")
ap.add_argument("--clave", default="clave-curso")
ap.add_argument("--cantidad", type=int, default=10)
ap.add_argument("--pausa", type=float, default=1.0)
a = ap.parse_args()

campo = next(c for c in proyecto.CAMPOS if c["nombre"] == proyecto.CAMPO_PRINCIPAL)
valor = proyecto.EJEMPLO[proyecto.CAMPO_PRINCIPAL]
for i in range(1, a.cantidad + 1):
    paso = random.uniform(-3, 3)
    valor = valor + paso
    valor = max(campo.get("minimo", valor), min(campo.get("maximo", valor), valor))
    cuerpo = dict(proyecto.EJEMPLO)
    cuerpo[proyecto.CAMPO_PRINCIPAL] = round(valor) if campo["tipo"] == "entero" else round(valor, 1)
    try:
        r = requests.post(a.url + "/registros", json=cuerpo, headers={"X-API-Key": a.clave}, timeout=5)
        print(i, r.status_code, r.text.strip())
    except requests.RequestException as e:
        print(i, "error de red:", e)
    time.sleep(a.pausa)
