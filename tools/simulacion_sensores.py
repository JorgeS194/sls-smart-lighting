"""Simulación en Python (PC / VS Code) de los sensores de la Casa Inteligente.

Sensores simulados: PIR (Sala), HC-SR04 (Habitación 1) y LDR (Habitación 2).
Incluye clasificación de lecturas, manejo de eventos, manejo de excepciones,
persistencia del estado en JSON y exportación del historial a CSV.

Uso:
    python simulacion_sensores.py                 # 30 ciclos, pausa de 0.2 s
    python simulacion_sensores.py --ciclos 60 --pausa 0 --semilla 7
"""
import argparse
import csv
import json
import os
import random
import time
from datetime import datetime

# ==================== CONFIGURACIÓN (mismos valores que main.py) ====================
ARCHIVO_JSON = "estado.json"
ARCHIVO_CSV = "historial.csv"
UMBRAL_LUZ = 2000          # valor ADC que separa "oscuro" de "claro"
HISTERESIS_LUZ = 150       # margen anti-parpadeo
DISTANCIA_PRESENCIA = 100  # cm: menos que esto = presencia
DISTANCIA_CERCA = 50       # cm: menos que esto = persona muy cerca
CICLOS_APAGADO = 3         # ciclos sin presencia antes de apagar (equivale a TIEMPO_APAGADO)
CAMPOS_CSV = ["fecha_hora", "ciclo", "sensor", "valor", "unidad",
              "clasificacion", "evento"]


# ==================== EXCEPCIÓN PROPIA ====================
class SensorError(Exception):
    """Falla de lectura de un sensor (sin eco, valor fuera de rango, etc.)."""


# ==================== SENSORES SIMULADOS ====================
class Sensor:
    nombre = "SENSOR"
    zona = "ZONA"
    unidad = ""

    def __init__(self, prob_fallo=0.08):
        self.prob_fallo = prob_fallo

    def leer(self):
        """Devuelve la lectura o lanza SensorError."""
        if random.random() < self.prob_fallo:
            raise SensorError("{}: sin respuesta del sensor".format(self.nombre))
        valor = self._medir()
        if not self._valido(valor):
            raise SensorError("{}: valor fuera de rango ({})".format(self.nombre, valor))
        return valor

    def _medir(self):
        raise NotImplementedError

    def _valido(self, valor):
        return True


class SensorPIR(Sensor):
    nombre, zona, unidad = "PIR", "SALA", "bool"

    def __init__(self, prob_fallo=0.08):
        super().__init__(prob_fallo)
        self.activo = False

    def _medir(self):
        if random.random() < 0.25:        # a veces cambia de estado
            self.activo = not self.activo
        return 1 if self.activo else 0

    def _valido(self, valor):
        return valor in (0, 1)


class SensorUltrasonico(Sensor):
    nombre, zona, unidad = "HC-SR04", "HABITACION_1", "cm"

    def __init__(self, prob_fallo=0.08):
        super().__init__(prob_fallo)
        self.distancia = 200.0

    def _medir(self):
        self.distancia += random.uniform(-60, 60)
        self.distancia = max(5.0, min(350.0, self.distancia))
        return round(self.distancia, 1)

    def _valido(self, valor):
        return 2 <= valor <= 400          # rango real del HC-SR04


class SensorLDR(Sensor):
    nombre, zona, unidad = "LDR", "HABITACION_2", "adc"

    def __init__(self, prob_fallo=0.08):
        super().__init__(prob_fallo)
        self.valor = 800

    def _medir(self):
        self.valor += random.randint(-700, 700)
        self.valor = max(0, min(4095, self.valor))
        return self.valor

    def _valido(self, valor):
        return 0 <= valor <= 4095         # ADC de 12 bits


# ==================== CLASIFICACIÓN DE LECTURAS ====================
def clasificar_pir(valor):
    return "PRESENCIA" if valor == 1 else "SIN_PRESENCIA"


def clasificar_distancia(cm):
    if cm < DISTANCIA_CERCA:
        return "MUY_CERCA"
    if cm < DISTANCIA_PRESENCIA:
        return "PRESENCIA"
    return "SIN_PRESENCIA"


def clasificar_luz(valor, era_oscuro):
    """Histéresis: el umbral cambia según el estado anterior."""
    limite = UMBRAL_LUZ - HISTERESIS_LUZ if era_oscuro else UMBRAL_LUZ + HISTERESIS_LUZ
    return "OSCURO" if valor > limite else "CLARO"


# ==================== PERSISTENCIA JSON ====================
def estado_inicial():
    return {
        "leds": {"SALA": False, "HABITACION_1": False, "HABITACION_2": False},
        "clasificacion": {"SALA": "SIN_PRESENCIA", "HABITACION_1": "SIN_PRESENCIA",
                          "HABITACION_2": "CLARO"},
        "ciclos_sin_presencia": {"SALA": 0, "HABITACION_1": 0},
        "contadores": {"lecturas": 0, "eventos": 0, "fallos": 0},
        "ultima_actualizacion": None,
    }


def cargar_estado():
    """Carga estado.json; si falta o está dañado, arranca con un estado limpio."""
    try:
        with open(ARCHIVO_JSON, encoding="utf-8") as f:
            estado = json.load(f)
        print("[JSON] Estado restaurado desde", ARCHIVO_JSON)
        return estado
    except FileNotFoundError:
        print("[JSON] No existe", ARCHIVO_JSON, "- se crea un estado nuevo")
    except json.JSONDecodeError as e:
        print("[JSON] Archivo dañado ({}) - se crea un estado nuevo".format(e))
    return estado_inicial()


def guardar_estado(estado):
    """Escribe el JSON en un archivo temporal y lo reemplaza (evita corrupción)."""
    estado["ultima_actualizacion"] = datetime.now().isoformat(timespec="seconds")
    temporal = ARCHIVO_JSON + ".tmp"
    try:
        with open(temporal, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)
        os.replace(temporal, ARCHIVO_JSON)
    except OSError as e:
        print("[JSON] No se pudo guardar el estado:", e)


# ==================== EXPORTACIÓN CSV ====================
def exportar_csv(historial):
    """Agrega el historial al CSV (crea el encabezado si el archivo es nuevo)."""
    if not historial:
        return
    nuevo = not os.path.exists(ARCHIVO_CSV)
    try:
        with open(ARCHIVO_CSV, "a", newline="", encoding="utf-8") as f:
            escritor = csv.DictWriter(f, fieldnames=CAMPOS_CSV)
            if nuevo:
                escritor.writeheader()
            escritor.writerows(historial)
        print("[CSV] {} registros exportados a {}".format(len(historial), ARCHIVO_CSV))
    except PermissionError:
        print("[CSV] Sin permiso: cierra", ARCHIVO_CSV, "si está abierto en Excel")
    except OSError as e:
        print("[CSV] No se pudo exportar:", e)


# ==================== MANEJO DE EVENTOS ====================
def manejar_evento(estado, zona, evento, detalle=""):
    """Reacciona al evento: actúa sobre el LED de la zona y cuenta el evento."""
    if evento in ("ENCENDER_LUZ",):
        estado["leds"][zona] = True
    elif evento in ("APAGAR_LUZ",):
        estado["leds"][zona] = False
    estado["contadores"]["eventos"] += 1
    print("   -> EVENTO [{}] {} {}".format(zona, evento, detalle).rstrip())


def procesar_clasificacion(estado, sensor, valor, clase):
    """Detecta cambios de clasificación y dispara el evento que corresponda."""
    zona = sensor.zona
    anterior = estado["clasificacion"][zona]
    evento = ""

    if zona == "HABITACION_2":                       # LDR
        if clase != anterior:
            evento = "ENCENDER_LUZ" if clase == "OSCURO" else "APAGAR_LUZ"
    else:                                            # PIR y HC-SR04
        hay = clase != "SIN_PRESENCIA"
        sin = estado["ciclos_sin_presencia"]
        if hay:
            sin[zona] = 0
            if not estado["leds"][zona]:
                evento = "ENCENDER_LUZ"
        else:
            sin[zona] += 1
            if estado["leds"][zona] and sin[zona] >= CICLOS_APAGADO:
                evento = "APAGAR_LUZ"

    estado["clasificacion"][zona] = clase
    if evento:
        manejar_evento(estado, zona, evento, "({} {})".format(valor, sensor.unidad))
    return evento


# ==================== PROGRAMA PRINCIPAL ====================
def simular(ciclos, pausa):
    sensores = [SensorPIR(), SensorUltrasonico(), SensorLDR()]
    estado = cargar_estado()
    historial = []

    try:
        for ciclo in range(1, ciclos + 1):
            print("Ciclo {}".format(ciclo))
            for s in sensores:
                fila = {"fecha_hora": datetime.now().isoformat(timespec="seconds"),
                        "ciclo": ciclo, "sensor": s.nombre, "unidad": s.unidad}
                try:
                    valor = s.leer()
                    if isinstance(s, SensorPIR):
                        clase = clasificar_pir(valor)
                    elif isinstance(s, SensorUltrasonico):
                        clase = clasificar_distancia(valor)
                    else:
                        clase = clasificar_luz(valor, estado["clasificacion"][s.zona] == "OSCURO")
                    estado["contadores"]["lecturas"] += 1
                    print("  {:8} {:>7} {:3} -> {}".format(s.nombre, valor, s.unidad, clase))
                    fila.update(valor=valor, clasificacion=clase,
                                evento=procesar_clasificacion(estado, s, valor, clase))
                except SensorError as e:
                    estado["contadores"]["fallos"] += 1
                    print("  [FALLO] {}".format(e))
                    fila.update(valor="", clasificacion="ERROR", evento="FALLO_SENSOR")
                historial.append(fila)
            guardar_estado(estado)       # el estado sobrevive si el programa se cierra
            time.sleep(pausa)
    except KeyboardInterrupt:
        print("\nSimulación detenida por el usuario")
    finally:
        guardar_estado(estado)
        exportar_csv(historial)
    return estado


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulación de sensores - Casa Inteligente")
    parser.add_argument("--ciclos", type=int, default=30)
    parser.add_argument("--pausa", type=float, default=0.2)
    parser.add_argument("--semilla", type=int, default=None,
                        help="semilla del azar (para repetir una corrida)")
    args = parser.parse_args()
    if args.semilla is not None:
        random.seed(args.semilla)
    final = simular(args.ciclos, args.pausa)
    print("\nResumen:", final["contadores"])
