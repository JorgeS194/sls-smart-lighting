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
    return None
