"""WiFi/MQTT en un hilo: el ciclo de sensores solo encola, nunca usa sockets.

El hilo es el único dueño de WLAN y MQTT. El candado protege la cola y nunca
se mantiene durante operaciones de red. QoS 1 puede entregar duplicados;
(dispositivo, sesion, secuencia) permite identificarlos en el futuro backend.
"""
import time
import config
import mensajes

_servicio = None


class ServicioRed:
    def __init__(self, wlan, cliente_mqtt, candado, sesion, ssid=None, password=None):
        self.wlan = wlan
        self.cliente_mqtt = cliente_mqtt
        self.candado = candado
        self.sesion = sesion
        self.ssid = config.WIFI_SSID if ssid is None else ssid
        self.password = config.WIFI_PASS if password is None else password
        self.cola = []
        self.secuencia = 0
        self.descartados = 0
        self.cliente = None
        self.esperando_wifi = False
        self.inicio_wifi = 0
        self.ultimo_fallo = None
        self.ultimo_envio = time.ticks_ms()
        base = "{}/{}".format(config.MQTT_PREFIJO, config.MQTT_DISPOSITIVO)
        self.topico_eventos = (base + "/eventos").encode()
        self.topico_latido = (base + "/conexion").encode()

    def encolar(self, zona, evento, valor="", luz=None):
        # Solo el ciclo principal produce eventos. Serializar antes del candado.
        self.secuencia += 1
        dato = mensajes.evento(zona, evento, valor, luz, self.secuencia,
                               self.sesion, time.ticks_ms())
        with self.candado:
            if len(self.cola) >= config.RED_MAX_PENDIENTES:
                self.cola.pop(0)
                self.descartados += 1
            self.cola.append((self.secuencia, dato))

    def _cerrar(self):
        if self.cliente is not None:
            # Cerrar también si CONNECT no llegó a terminar.
            sock = getattr(self.cliente, "sock", None)
            if sock is not None:
                try:
                    sock.close()
                except OSError:
                    pass
            self.cliente = None

    def paso(self):
        """Un intento del hilo; no se llama desde el ciclo de sensores."""
        ahora = time.ticks_ms()
        if self.ultimo_fallo is not None:
            if time.ticks_diff(ahora, self.ultimo_fallo) < config.RED_REINTENTO_MS:
                return
            self.ultimo_fallo = None
        try:
            if not self.wlan.isconnected():
                self._cerrar()
                if not self.esperando_wifi:
                    self.wlan.active(True)
                    self.wlan.connect(self.ssid, self.password)
                    self.inicio_wifi = ahora
                    self.esperando_wifi = True
                    print("[RED] Conectando WiFi")
                elif time.ticks_diff(ahora, self.inicio_wifi) >= config.RED_WIFI_TIMEOUT_MS:
                    self.wlan.disconnect()
                    raise OSError("Tiempo de espera WiFi agotado")
                return
            self.esperando_wifi = False
            if self.cliente is None:
                identificador = "sls-{}-{}".format(config.MQTT_DISPOSITIVO, self.sesion)
                self.cliente = self.cliente_mqtt(
                    identificador.encode(), config.MQTT_SERVIDOR,
                    port=config.MQTT_PUERTO, keepalive=config.MQTT_KEEPALIVE)
                # umqtt.simple reciente admite timeout; Wokwi puede traer la antigua.
                try:
                    self.cliente.connect(timeout=config.RED_TIMEOUT_S)
                except TypeError:
                    self.cliente.connect()
                self.cliente.sock.settimeout(config.RED_TIMEOUT_S)
                print("[RED] MQTT conectado: {}".format(self.topico_eventos.decode()))
                self._latido()
            with self.candado:
                pendiente = self.cola[0] if self.cola else None
            if pendiente is not None:
                self.cliente.sock.settimeout(config.RED_TIMEOUT_S)
                self.cliente.publish(self.topico_eventos, pendiente[1], qos=1, retain=False)
                # El productor pudo descartar este elemento mientras se enviaba.
                with self.candado:
                    if self.cola and self.cola[0][0] == pendiente[0]:
                        self.cola.pop(0)
                self.ultimo_envio = time.ticks_ms()
            elif time.ticks_diff(ahora, self.ultimo_envio) >= config.RED_LATIDO_MS:
                self._latido()
        except Exception as error:
            # MQTTException de umqtt no deriva de OSError. Ningún error de transporte
            # debe terminar el hilo; el mensaje de consola permite diagnosticarlo.
            self._cerrar()
            self.esperando_wifi = False
            self.ultimo_fallo = time.ticks_ms()
            print("[RED] Sin conexion; se reintentara:", error)

    def _latido(self):
        self.cliente.sock.settimeout(config.RED_TIMEOUT_S)
        self.cliente.publish(self.topico_latido,
                             mensajes.latido(self.sesion, self.descartados, time.ticks_ms()),
                             qos=1, retain=False)
        self.ultimo_envio = time.ticks_ms()

    def ejecutar(self):
        while True:
            self.paso()
            time.sleep_ms(100)


def iniciar():
    """Inicia una sola tarea de red. Si faltan módulos, las luces siguen solas."""
    global _servicio
    if not config.HABILITAR_RED or _servicio is not None:
        return
    if not config.MQTT_SERVIDOR:
        print("[RED] Configura MQTT_SERVIDOR; control local activo")
        return
    try:
        import _thread
        import network
        import os
        from binascii import hexlify
        from umqtt.simple import MQTTClient
        ssid, password = config.WIFI_SSID, config.WIFI_PASS
        if config.ENTORNO == "real":
            # Dentro del arranque protegido: un secrets.py ausente no para las luces.
            from secrets import WIFI_SSID, WIFI_PASS
            ssid, password = WIFI_SSID, WIFI_PASS
        sesion = hexlify(os.urandom(4)).decode()
        servicio = ServicioRed(network.WLAN(network.STA_IF), MQTTClient,
                               _thread.allocate_lock(), sesion, ssid, password)
        _thread.start_new_thread(servicio.ejecutar, ())
        _servicio = servicio
    except (ImportError, OSError, RuntimeError, MemoryError) as error:
        print("[RED] No se pudo iniciar; control local activo:", error)


def encolar(zona, evento, valor="", luz=None):
    if _servicio is not None:
        _servicio.encolar(zona, evento, valor, luz)
