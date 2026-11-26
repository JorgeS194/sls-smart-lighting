# Configuracion del proyecto de tu grupo: es el UNICO archivo que cambia entre proyectos.
# Ficha del Smart Lighting System (SLS): casa inteligente con ESP32, PIR, HC-SR04 y LDR.
NOMBRE = "Smart Lighting System (SLS)"
TABLA = "telemetria_sls"         # nombre de la tabla en la base de datos
TEMA = "sls"                     # tema MQTT: utp/ds8/<usuario>/<TEMA>/<TEMA_DATOS>
TEMA_DATOS = "telemetria"
DB = "proyecto.db"

# Un diccionario por cada dato que mide o reporta tu dispositivo.
#   tipo: "entero", "real" o "texto"     obligatorio: True/False
#   minimo / maximo: limites opcionales (numeros)     permitidos: lista opcional de valores validos
CAMPOS = [
    # Zona de la casa que reporta (SALA, HABITACION_1, HABITACION_2...). Texto libre a proposito:
    # asi las pruebas de inyeccion SQL de las Partes D e I pueden guardar el texto malicioso.
    {"nombre": "zona", "tipo": "texto", "obligatorio": True},
    # HC-SR04: 2 a 400 cm es su rango fisico. Opcional: sin eco el dispositivo no manda este dato
    # (el contrato del SLS usa "sin lectura" en vez de inventar un cero).
    {"nombre": "distancia_cm", "tipo": "real", "obligatorio": False, "minimo": 2, "maximo": 400},
    # LDR leido por el ADC de 12 bits del ESP32: 0 a 4095.
    {"nombre": "luz_adc", "tipo": "entero", "obligatorio": True, "minimo": 0, "maximo": 4095},
    # PIR: 0 = sin movimiento, 1 = movimiento.
    {"nombre": "movimiento", "tipo": "entero", "obligatorio": True, "permitidos": [0, 1]},
    # Estado de la luz de la zona: 0 = apagada, 1 = encendida.
    {"nombre": "luz_encendida", "tipo": "entero", "obligatorio": True, "permitidos": [0, 1]},
]
CAMPO_PRINCIPAL = "luz_adc"      # campo numerico que se resume y se promedia por hora
EJEMPLO = {"zona": "SALA", "distancia_cm": 45.5, "luz_adc": 2150, "movimiento": 1, "luz_encendida": 1}   # un mensaje valido


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
