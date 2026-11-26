# Configuracion del proyecto de tu grupo: es el UNICO archivo que cambia entre proyectos.
# Completa la ficha de la Parte A. Mira ejemplos/ para ver tres proyectos distintos ya configurados.
NOMBRE = "ESCRIBE EL NOMBRE DE TU PROYECTO"
TABLA = "registros"              # nombre de la tabla en la base de datos
TEMA = "tuproyecto"              # tema MQTT: utp/ds8/<usuario>/<TEMA>/<TEMA_DATOS>
TEMA_DATOS = "telemetria"
DB = "proyecto.db"

# Un diccionario por cada dato que mide o reporta tu dispositivo.
#   tipo: "entero", "real" o "texto"     obligatorio: True/False
#   minimo / maximo: limites opcionales (numeros)     permitidos: lista opcional de valores validos
# Ejemplo:  {"nombre": "temperatura", "tipo": "real", "obligatorio": True, "minimo": -30, "maximo": 30},
CAMPOS = [
]
CAMPO_PRINCIPAL = ""             # campo numerico que se resume y se promedia por hora
EJEMPLO = {}                     # un mensaje valido de ejemplo con tus campos


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
