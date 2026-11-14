"""Estado observado: el firmware conserva el control y sus temporizadores."""
from copy import deepcopy
from datetime import datetime, timezone
from .receptor import SENSORES


def estado_inicial():
    return {"zonas": {zona: {"sensor": sensor, "valor": None, "clasificacion": None,
                            "luz": None, "ultima_actualizacion": None}
                      for zona, sensor in SENSORES.items()},
            "lecturas": 0, "ultima_actualizacion": None}


def procesar(estado, mensaje):
    nuevo = deepcopy(estado)
    fecha = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    zona = nuevo["zonas"][mensaje["zona"]]
    sensor, valor = mensaje["sensor"], mensaje["valor"]
    if sensor == "PIR":
        clase = "PRESENCIA" if valor else "SIN_PRESENCIA"
    elif sensor == "HC-SR04":
        clase = "MUY_CERCA" if valor < 30 else "PRESENCIA" if valor < 100 else "SIN_PRESENCIA"
    else:
        limite = 1850 if zona["clasificacion"] == "OSCURO" else 2150
        clase = "OSCURO" if valor > limite else "CLARO"
    zona.update(valor=valor, clasificacion=clase, ultima_actualizacion=fecha)
    if "luz" in mensaje:
        zona["luz"] = mensaje["luz"]
    elif mensaje["evento"] in ("LUZ_ENCENDIDA", "ENCENDER_LUZ"):
        zona["luz"] = True
    elif mensaje["evento"] in ("LUZ_APAGADA", "APAGAR_LUZ"):
        zona["luz"] = False
    nuevo["lecturas"] += 1
    nuevo["ultima_actualizacion"] = fecha
    fila = dict(fecha_hora=fecha, **mensaje, clasificacion=clase)
    fila["luz"] = zona["luz"]
    return nuevo, fila
