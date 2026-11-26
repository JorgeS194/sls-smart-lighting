# Configuracion del proyecto de tu grupo: es el UNICO archivo que cambia entre proyectos.
# Completa la ficha de la Parte A. Mira ejemplos/ para ver tres proyectos distintos ya configurados.
NOMBRE = "SLS - Smart Lighting System"
TABLA = "registros"              # nombre de la tabla en la base de datos
TEMA = "sls-smart-lighting"      # tema MQTT: utp/ds8/<usuario>/<TEMA>/<TEMA_DATOS>
TEMA_DATOS = "telemetria"
DB = "proyecto.db"

# Un diccionario por cada dato que mide o reporta tu dispositivo.
#   tipo: "entero", "real" o "texto"     obligatorio: True/False
#   minimo / maximo: limites opcionales (numeros)     permitidos: lista opcional de valores validos
# Ejemplo:  {"nombre": "temperatura", "tipo": "real", "obligatorio": True, "minimo": -30, "maximo": 30},
CAMPOS = [
    {"nombre": "dispositivo",      "tipo": "texto",  "obligatorio": True},
    {"nombre": "pir",              "tipo": "entero", "obligatorio": True,  "permitidos": [0, 1]},
    {"nombre": "ldr_adc",          "tipo": "entero", "obligatorio": True,  "minimo": 0, "maximo": 4095},
    {"nombre": "distancia_cm",     "tipo": "real",   "obligatorio": False, "minimo": 2, "maximo": 400},
    {"nombre": "luz_sala",         "tipo": "entero", "obligatorio": True,  "permitidos": [0, 1]},
    {"nombre": "luz_habitacion_1", "tipo": "entero", "obligatorio": True,  "permitidos": [0, 1]},
    {"nombre": "luz_habitacion_2", "tipo": "entero", "obligatorio": True,  "permitidos": [0, 1]},
]
CAMPO_PRINCIPAL = "ldr_adc"      # campo numerico que se resume y se promedia por hora
EJEMPLO = {"dispositivo": "demo-sala-francesco", "pir": 0, "ldr_adc": 2593,
           "distancia_cm": 60.0, "luz_sala": 0, "luz_habitacion_1": 1, "luz_habitacion_2": 1}


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
