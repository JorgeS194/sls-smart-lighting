# config.py: todo lo que se puede ajustar vive aquí.

ENTORNO = "wokwi"   # "wokwi" o "real" (por ahora no cambia nada; se usará en la Etapa 3)

# ==================== CONFIGURACIÓN (puedes modificarla) ====================
TIEMPO_APAGADO = 5          # segundos que la luz sigue encendida tras perder la presencia (Sala y Habitación 1)
DISTANCIA_PRESENCIA = 100   # cm: si el HC-SR04 mide menos que esto, hay presencia
UMBRAL_LUZ = 2000           # valor del ADC (0-4095) que separa "oscuro" de "claro"
HISTERESIS_LUZ = 150        # margen para evitar parpadeos cerca del umbral
OSCURO_ES_VALOR_ALTO = True # True: oscuridad = valor ADC alto | False: oscuridad = valor ADC bajo
DEPURAR_LDR = False         # True: imprime el valor del LDR cada segundo (para calibrar el umbral)
PAUSA_CICLO_MS = 100        # pausa entre cada revisión de los sensores
ARCHIVO_CSV = "historial.csv"   # archivo donde se guarda el historial (solo ESP32 real)
MAX_HISTORIAL = 50              # eventos que se conservan en memoria RAM

# ==================== PINES (según tu circuito) ====================
PIN_PIR = 13            # Sala: salida del PIR
PIN_TRIG = 14          # Habitación 1: TRIG del HC-SR04
PIN_ECHO = 12           # Habitación 1: ECHO del HC-SR04
PIN_LDR = 34               # Habitación 2: salida analógica (AO) del LDR

PIN_DS = 21            # 74HC595: DS   (datos)
PIN_STCP = 22          # 74HC595: STCP (latch)
PIN_SHCP = 23          # 74HC595: SHCP (reloj)

# Salidas del 74HC595 asignadas a cada LED
BIT_SALA = 7   # Q7 -> LED rojo
BIT_HAB1 = 6   # Q6 -> LED verde
BIT_HAB2 = 5   # Q5 -> LED azul