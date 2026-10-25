# Backend SLS

Backend en **Python 3** (requisito de la guía del curso). Recibe los mensajes del ESP32, los valida, los procesa y los guarda.

## Implementación actual

- `servidor.py`: HTTP local y dashboard, con biblioteca estándar de Python 3.9+.
- `estado.py`: contrato v1 del firmware, deduplicación y estado de las zonas.
- `mqtt_receptor.py`: recepción MQTT opcional, sin publicar comandos.
- `datos/sls.sqlite3`: persistencia transaccional de eventos, ignorada por Git.

```bash
python backend/servidor.py
```

Abre http://127.0.0.1:8000. Opciones: `--port 8001` y `--datos RUTA`.
Solo escucha en loopback; no es un servidor de producción ni queda expuesto
a la red local. Ctrl+C lo detiene. El dashboard/importación no requieren pip.

| Ruta | Función |
|---|---|
| `GET /api/estado` | Zonas, total, últimos 1000 eventos y estado MQTT |
| `POST /api/eventos` | Un JSON v1 o lista de hasta 1000; máximo 512000 bytes |
| `GET /api/exportar.csv` | Exporta hasta 100000 eventos sin modificar datos |

La recepción se fecha en UTC. `tiempo_ms` sigue siendo el contador del ESP32.
Se conserva la última lectura numérica al recibir un cambio de luz sin lectura.
El estado respeta la secuencia dentro de la última sesión observada de cada
dispositivo; reenvíos conocidos de sesiones anteriores no revierten el estado.
La interfaz representa una casa; varias casas requieren un selector de dispositivo.

Se usa SQLite para transacciones y deduplicación, JSON para consultar el estado
y CSV para exportar el historial, en lugar de reescribir archivos en cada mensaje.
La demo del navegador no guarda eventos en esta base.

## Dependencias
Solo para recibir MQTT, instala las dependencias opcionales:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate
pip install -r backend/requirements.txt
```

Cada vez que se agregue una librería, se agrega a `requirements.txt` en el mismo Pull Request.

Después de elegir un broker:

```bash
python backend/servidor.py --mqtt-host BROKER_ELEGIDO --mqtt-port 1883 --topic "utp-sls/jorge-s194/casa-01/eventos"
```

Paho usa callbacks v2 y reconexión en segundo plano. Solo se suscribe; nunca
publica comandos. HTTP continúa disponible si el broker no responde. Esta primera
versión es MQTT sin autenticación/TLS, como el firmware actual; para datos privados
se requiere agregarlos en ambos extremos. No se contacta un broker por defecto.

Referencia: [API oficial de Paho](https://eclipse.dev/paho/clients/python/docs/).
La integración externa no está validada. Las pruebas usan SQLite temporal y HTTP local.
