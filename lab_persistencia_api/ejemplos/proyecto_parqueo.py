# Ejemplo: estacionamiento inteligente (sensor ultrasonico por plaza)
NOMBRE = "Estacionamiento inteligente"
TABLA = "registros"
TEMA = "parqueo"
TEMA_DATOS = "telemetria"
DB = "proyecto.db"
CAMPOS = [
    {"nombre": "plaza", "tipo": "texto", "obligatorio": True},
    {"nombre": "distancia_cm", "tipo": "real", "obligatorio": True, "minimo": 2, "maximo": 400},
    {"nombre": "ocupada", "tipo": "entero", "obligatorio": True, "permitidos": [0, 1]},
]
CAMPO_PRINCIPAL = "distancia_cm"
EJEMPLO = {"plaza": "A1", "distancia_cm": 120.5, "ocupada": 0}
