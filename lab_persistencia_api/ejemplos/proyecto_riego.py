# Configuracion del proyecto del grupo: es el UNICO archivo que cambia entre proyectos.
NOMBRE = "Riego automatico"
TABLA = "registros"              # nombre de la tabla en la base de datos
TEMA = "riego"                   # tema MQTT: utp/ds8/<usuario>/<TEMA>/<TEMA_DATOS>
TEMA_DATOS = "telemetria"
DB = "proyecto.db"

# Un diccionario por cada dato que mide o reporta tu dispositivo.
#   tipo: "entero", "real" o "texto"     obligatorio: True/False
#   minimo / maximo: limites opcionales (numeros)     permitidos: lista opcional de valores validos
CAMPOS = [
    {"nombre": "humedad", "tipo": "entero", "obligatorio": True, "minimo": 0, "maximo": 100},
    {"nombre": "bomba",   "tipo": "entero", "obligatorio": True, "permitidos": [0, 1]},
    {"nombre": "modo",    "tipo": "texto",  "obligatorio": True},
    {"nombre": "umbral",  "tipo": "entero", "obligatorio": False, "minimo": 10, "maximo": 90},
]
CAMPO_PRINCIPAL = "humedad"      # campo numerico que se resume y se promedia por hora
EJEMPLO = {"humedad": 50, "bomba": 0, "modo": "AUTO", "umbral": 40}   # un mensaje valido


# ---- Comprobacion automatica (no modificar) ----
def _comprobar():
    import re
    if not CAMPOS:
        raise SystemExit("proyecto.py: CAMPOS esta vacio. Completa la ficha del proyecto (Parte A de la guia)")
    nombres = []
    for c in CAMPOS:
        n = c.get("nombre", "")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", n):
            raise SystemExit("proyecto.py: el nombre de campo %r no es valido (minusculas, digitos y _; empieza con letra)" % n)
        if n in ("id", "fecha") or n in nombres:
            raise SystemExit("proyecto.py: el nombre %r esta repetido o reservado" % n)
        if c.get("tipo") not in ("entero", "real", "texto"):
            raise SystemExit("proyecto.py: el campo %s tiene un tipo desconocido (use entero, real o texto)" % n)
        nombres.append(n)
    if not re.fullmatch(r"[a-z][a-z0-9_]*", TABLA):
        raise SystemExit("proyecto.py: TABLA no es un nombre valido")
    principal = [c for c in CAMPOS if c["nombre"] == CAMPO_PRINCIPAL]
    if not principal or principal[0]["tipo"] == "texto":
        raise SystemExit("proyecto.py: CAMPO_PRINCIPAL debe ser un campo numerico de CAMPOS")
    faltan = [n for n in nombres if n not in EJEMPLO and next(c for c in CAMPOS if c["nombre"] == n).get("obligatorio")]
    if faltan:
        raise SystemExit("proyecto.py: EJEMPLO no tiene los campos obligatorios " + ", ".join(faltan))


_comprobar()
