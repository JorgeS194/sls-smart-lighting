"""Eventos del contrato v1 del firmware, persistencia y estado del dashboard."""
import json
import math
import sqlite3
import threading
from datetime import datetime, timezone

ZONAS = {"SALA": "PIR", "HABITACION 1": "HC-SR04", "HABITACION 2": "LDR"}
EVENTOS = {"IRQ_PIR", "PRESENCIA", "SIN_PRESENCIA", "OSCURIDAD",
           "LUZ_SUFICIENTE", "LUZ_ENCENDIDA", "LUZ_APAGADA"}


def validar(dato):
    if not isinstance(dato, dict) or type(dato.get("version")) is not int or dato["version"] != 1:
        raise ValueError("Se requiere un evento JSON con version: 1")
    for campo in ("dispositivo", "sesion"):
        if not isinstance(dato.get(campo), str) or not 1 <= len(dato[campo]) <= 80:
            raise ValueError("Campo inválido: " + campo)
    for campo in ("secuencia", "tiempo_ms"):
        if type(dato.get(campo)) is not int or not (1 if campo == "secuencia" else 0) <= dato[campo] < 2**63:
            raise ValueError("Campo inválido: " + campo)
    if not isinstance(dato.get("zona"), str) or dato["zona"] not in ZONAS or dato.get("sensor") != ZONAS[dato["zona"]]:
        raise ValueError("La zona y el sensor no coinciden")
    if not isinstance(dato.get("evento"), str) or dato["evento"] not in EVENTOS or type(dato.get("luz")) is not bool:
        raise ValueError("Evento o estado de luz inválido")
    valor = dato.get("valor")
    if valor != "" and (type(valor) not in (int, float) or not math.isfinite(valor)):
        raise ValueError("valor debe ser un número finito o texto vacío")
    permitidos = ("version", "dispositivo", "sesion", "secuencia", "tiempo_ms",
                  "zona", "sensor", "evento", "valor", "luz")
    return {clave: dato[clave] for clave in permitidos}


class Almacen:
    def __init__(self, archivo):
        self.lock = threading.RLock()
        self.db = sqlite3.connect(str(archivo), check_same_thread=False)
        self.db.execute("""CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY, dispositivo TEXT, sesion TEXT, secuencia INTEGER,
            recibido TEXT, dato TEXT, UNIQUE(dispositivo, sesion, secuencia))""")
        self.db.commit()

    def cerrar(self):
        self.db.close()

    def agregar(self, datos):
        if not isinstance(datos, list) or not 1 <= len(datos) <= 1000:
            raise ValueError("Importa de 1 a 1000 eventos por lote")
        limpios = [validar(dato) for dato in datos]
        recibidos = datetime.now(timezone.utc).isoformat()
        with self.lock, self.db:
            antes = self.db.total_changes
            for dato in limpios:
                self.db.execute("INSERT OR IGNORE INTO eventos VALUES (NULL,?,?,?,?,?)", (
                    dato["dispositivo"], dato["sesion"], dato["secuencia"], recibidos,
                    json.dumps(dato, ensure_ascii=False)))
            return self.db.total_changes - antes

    def eventos(self, limite=1000):
        with self.lock:
            filas = self.db.execute("SELECT id, recibido, dato FROM eventos ORDER BY id DESC LIMIT ?",
                                    (limite,)).fetchall()
        return [dict(json.loads(dato), id=identificador, recibido=fecha)
                for identificador, fecha, dato in reversed(filas)]

    def estado(self):
        # Seleccionar por secuencia dentro de la última sesión recibida de cada
        # dispositivo: un reenvío atrasado no debe revertir una luz más reciente.
        with self.lock:
            cantidad = self.db.execute("SELECT COUNT(*) FROM eventos").fetchone()[0]
            filas = self.db.execute("SELECT id, recibido, dato FROM eventos ORDER BY id DESC").fetchall()
        zonas = {nombre: {"nombre": nombre, "sensor": sensor, "luz": None,
                          "valor": None, "lectura": None, "presencia": None,
                          "evento": None, "recibido": None}
                 for nombre, sensor in ZONAS.items()}
        sesiones, recientes = {}, {}
        datos = [dict(json.loads(texto), id=identificador, recibido=fecha)
                 for identificador, fecha, texto in filas]
        vistas = set()
        for dato in reversed(datos):
            clave_sesion = (dato["dispositivo"], dato["sesion"])
            if clave_sesion not in vistas:
                vistas.add(clave_sesion)
                sesiones[dato["dispositivo"]] = dato["sesion"]
        for dato in datos:
            dispositivo = dato["dispositivo"]
            if sesiones[dispositivo] != dato["sesion"]:
                continue
            clave = (dispositivo, dato["zona"])
            if clave not in recientes or dato["secuencia"] > recientes[clave]["secuencia"]:
                recientes[clave] = dato
        for dato in sorted(recientes.values(), key=lambda d: d["id"]):
            zonas[dato["zona"]].update(dato)
            anteriores = sorted((e for e in datos if e["zona"] == dato["zona"]
                                  and e["dispositivo"] == dato["dispositivo"] and e["sesion"] == dato["sesion"]),
                                 key=lambda e: e["secuencia"])
            for evento in anteriores:
                if evento["sensor"] != "PIR" and type(evento["valor"]) in (int, float):
                    zonas[dato["zona"]]["lectura"] = evento["valor"]
                if evento["evento"] in ("PRESENCIA", "SIN_PRESENCIA"):
                    zonas[dato["zona"]]["presencia"] = evento["evento"] == "PRESENCIA"
        return {"zonas": list(zonas.values()), "total_eventos": cantidad,
                "eventos": self.eventos(), "actualizado": filas[0][1] if filas else None}
