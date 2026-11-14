# historial.py: registro de eventos en RAM y, en un ESP32 real, en un CSV.
# Este archivo SOLO guarda y exporta eventos. Decidir QUÉ evento ocurrió
# es responsabilidad de logica.py; controlador.py registra sus decisiones
# y main.py registra directamente la IRQ del PIR.

import time
import config
# >>> INICIO CSV (descomentar SOLO en un ESP32 real; Wokwi no lo necesita)
# import os
# <<< FIN CSV

# Lista en RAM con los últimos eventos: (tiempo_ms, zona, evento, valor).
# Es "privada" (_): el resto del código la usa con registrar_evento() y eventos().
_eventos = []


def registrar_evento(zona, evento, valor=""):
    """Guarda el evento; zona es su nombre (texto), no el diccionario de zonas.py.

    Se conserva el parámetro zona para admitir llamadas existentes por nombre.
    La escritura al CSV está comentada.
    """
    ahora = time.ticks_ms()
    _eventos.append((ahora, zona, evento, valor))
    if len(_eventos) > config.MAX_HISTORIAL:
        _eventos.pop(0)   # descarta el más viejo para no llenar la RAM
    # >>> INICIO CSV (descomentar SOLO en un ESP32 real)
    # try:
    #     nuevo = config.ARCHIVO_CSV not in os.listdir()
    #     with open(config.ARCHIVO_CSV, "a") as f:
    #         if nuevo:
    #             f.write("tiempo_ms,zona,evento,valor\n")
    #         f.write("{},{},{},{}\n".format(ahora, zona, evento, valor))
    # except OSError as e:
    #     print("[CSV] No se pudo escribir:", e)
    # <<< FIN CSV


def eventos():
    """Devuelve la lista de eventos guardados en RAM (para el backend más adelante)."""
    return _eventos


def exportar_csv():
    """Imprime el CSV por el puerto serie para copiarlo (llamar desde la REPL)."""
    # >>> INICIO CSV (descomentar SOLO en un ESP32 real)
    # try:
    #     with open(config.ARCHIVO_CSV) as f:
    #         print(f.read())
    # except OSError:
    #     print("[CSV] Aun no existe", config.ARCHIVO_CSV)
    # <<< FIN CSV
    pass
