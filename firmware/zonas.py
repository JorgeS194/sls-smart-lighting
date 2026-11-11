# zonas.py: el ESTADO de cada zona de la casa (qué está pasando en cada una ahora mismo).
# Este archivo SOLO guarda datos: no lee sensores, no decide y no toca LEDs.
#   - logica.py actualiza estos diccionarios (presencia, luz, oscuro, ultima).
#   - main.py los pasa a controlador.py, que aplica los eventos y usa "bit" para el LED.
# Los diccionarios se comparten por referencia: todos los archivos ven los mismos
# objetos, así que NUNCA hay que reasignarlos (zonas.sala = ...), solo modificar sus claves.

import config

# Sala (PIR): presencia + temporizador de apagado.
sala = {"nombre": "SALA", "bit": config.BIT_SALA,
        "presencia": False, "luz": False, "ultima": 0}

# Habitación 1 (HC-SR04): presencia por distancia + temporizador de apagado.
hab1 = {"nombre": "HABITACION 1", "bit": config.BIT_HAB1,
        "presencia": False, "luz": False, "ultima": 0}

# Habitación 2 (LDR): oscuridad con histéresis (no usa temporizador).
hab2 = {"nombre": "HABITACION 2", "bit": config.BIT_HAB2,
        "oscuro": False, "luz": False}
