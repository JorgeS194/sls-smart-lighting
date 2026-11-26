import math

from proyecto import CAMPOS


def validar(d):
    """Devuelve un texto con el problema, o None si el mensaje es valido."""
    # TODO 7: recorre CAMPOS y comprueba, en este orden:
    #   - d es un diccionario (si no: "no es un objeto JSON");
    #   - cada campo obligatorio existe y no es None (si no: "falta el campo X"); un campo opcional ausente se omite;
    #   - tipo "texto": es str no vacio; tipo "entero": int (NO bool); tipo "real": int o float (NO bool);
    #     un numero debe ser finito (math.isfinite: json.loads acepta NaN e Infinity);
    #   - minimo, maximo y permitidos si el campo los define.
    if not isinstance(d, dict):
        return "no es un objeto JSON"
    for c in CAMPOS:
        n = c["nombre"]
        v = d.get(n)
        if v is None:
            if c.get("obligatorio"):
                return "falta el campo " + n
            continue                      # un campo opcional ausente se omite
        tipo = c["tipo"]
        if tipo == "texto":
            if not isinstance(v, str) or not v.strip():
                return "el campo %s debe ser un texto no vacio" % n
        else:
            # bool es subclase de int en Python (True == 1), por eso se descarta aparte.
            if isinstance(v, bool):
                return "el campo %s debe ser un numero, no un booleano" % n
            if tipo == "entero" and not isinstance(v, int):
                return "el campo %s debe ser un entero" % n
            if tipo == "real" and not isinstance(v, (int, float)):
                return "el campo %s debe ser un numero" % n
            # json.loads acepta NaN e Infinity. Solo un float puede no ser finito; con un
            # int muy grande math.isfinite lanzaria OverflowError.
            if isinstance(v, float) and not math.isfinite(v):
                return "el campo %s no es un numero finito" % n
            if "minimo" in c and v < c["minimo"]:
                return "el campo %s esta por debajo del minimo (%s)" % (n, c["minimo"])
            if "maximo" in c and v > c["maximo"]:
                return "el campo %s esta por encima del maximo (%s)" % (n, c["maximo"])
        if "permitidos" in c and v not in c["permitidos"]:
            return "el campo %s no esta entre los valores permitidos %s" % (n, c["permitidos"])
    return None
