# Ejemplo: monitoreo de una camara fria (temperatura, puerta y compresor)
NOMBRE = "Camara fria"
TABLA = "mediciones"
TEMA = "camara"
TEMA_DATOS = "telemetria"
DB = "proyecto.db"
CAMPOS = [
    {"nombre": "temperatura", "tipo": "real", "obligatorio": True, "minimo": -30, "maximo": 30},
    {"nombre": "puerta_abierta", "tipo": "entero", "obligatorio": True, "permitidos": [0, 1]},
    {"nombre": "compresor", "tipo": "texto", "obligatorio": True, "permitidos": ["ON", "OFF"]},
]
CAMPO_PRINCIPAL = "temperatura"
EJEMPLO = {"temperatura": 4.5, "puerta_abierta": 0, "compresor": "ON"}
