"""Puente opcional y solo de lectura: MQTT → validación → dashboard local."""
import json


def conectar(host, port, topic, almacen, estado):
    try:
        import paho.mqtt.client as mqtt
    except ImportError as error:
        raise SystemExit("Instala las dependencias opcionales: pip install -r backend/requirements.txt") from error
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    estado["configurado"] = True

    def on_connect(client, userdata, flags, reason_code, properties):
        estado["conectado"] = not reason_code.is_failure
        estado["error"] = str(reason_code) if reason_code.is_failure else None
        if not reason_code.is_failure:
            client.subscribe(topic, qos=1)

    def on_disconnect(client, userdata, flags, reason_code, properties):
        estado["conectado"] = False

    def on_message(client, userdata, message):
        try:
            if len(message.payload) > 16000:
                raise ValueError("Mensaje MQTT demasiado grande")
            almacen.agregar([json.loads(message.payload)])
            estado["error"] = None
        except (ValueError, UnicodeError) as error:
            estado["error"] = "Mensaje rechazado: " + str(error)

    cliente.on_connect = on_connect
    cliente.on_disconnect = on_disconnect
    cliente.on_message = on_message
    cliente.reconnect_delay_set(min_delay=1, max_delay=30)
    cliente.connect_async(host, port, keepalive=30)
    cliente.loop_start()
    return cliente
