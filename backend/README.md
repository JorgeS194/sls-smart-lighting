# Backend SLS

Python 3.8+. Ejecutar los comandos desde la raíz del repositorio.

## Desarrollo del dashboard sin broker

```powershell
python -m backend.main --sin-mqtt
```

API: http://127.0.0.1:8000. Este modo usa solo la biblioteca estándar.
Cargar una lectura de prueba desde otra terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/lecturas -Method Post -ContentType 'application/json' -Body '{"zona":"SALA","sensor":"PIR","valor":1,"evento":"PRESENCIA","luz":true}'
```

## Contrato para el dashboard

| Método | Ruta | Respuesta |
|---|---|---|
| GET | /api/salud | estado y mqtt_conectado |
| GET | /api/estado | zonas, lecturas y ultima_actualizacion |
| GET | /api/historial?limite=100&zona=SALA | objeto historial con filas más recientes primero |
| POST | /api/lecturas | 201 con el estado actualizado |
| POST | /api/comandos | 202 con estado enviado_al_broker y comando con id |

Zonas: SALA, HABITACION_1, HABITACION_2. El filtro zona del historial es
opcional. limite acepta 1–1000; predeterminado 100.
Cada entrada de zonas tiene sensor, valor, clasificacion, luz y
ultima_actualizacion. Las lecturas, clasificaciones, luces y fechas empiezan
en null hasta recibir información. Fechas ISO 8601 en UTC.
Cada fila del historial tiene fecha_hora, zona, sensor, valor, evento,
clasificacion y luz (booleano o null).

```javascript
const API = 'http://127.0.0.1:8000';
const estado = await fetch(`${API}/api/estado`).then(r => r.json());
console.log(estado.zonas.SALA.luz);
const respuesta = await fetch(`${API}/api/comandos`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({zona: 'SALA', accion: 'apagar'})
});
const resultado = await respuesta.json();
if (!respuesta.ok) throw new Error(resultado.error);
```

Acciones: encender, apagar, auto. El dashboard puede consultar el estado
cada segundo. Un 202 indica envío al broker; no confirma ejecución física.
La luz solo cambia con telemetría que incluya luz o evento de encendido/apagado.
Sin conexión MQTT, los comandos devuelven 503.
Errores JSON: {"error":"descripción"}. Códigos: 400 datos inválidos,
404 ruta inexistente, 413 cuerpo vacío o mayor de 16 KiB, 500 almacenamiento.

CORS permite http://localhost:5173. Para otro origen:

```powershell
python -m backend.main --sin-mqtt --origen http://localhost:3000
```

## MQTT y contrato con firmware

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements.txt
python -m backend.main --broker localhost --prefijo utp-sls-g1
```

El equipo debe elegir broker y usar el mismo prefijo en el ESP32.
No se desplegó infraestructura en la nube.

- ESP32 publica en utp-sls-g1/telemetria.
- ESP32 se suscribe a utp-sls-g1/comandos.
- Backend recibe y publica con QoS 1. Comandos sin retain.
- Reconexión con esperas entre 1 y 30 segundos.

Telemetría mínima:

```json
{"zona":"SALA","sensor":"PIR","valor":1,"evento":"PRESENCIA"}
```

Sensores: SALA/PIR (0 o 1), HABITACION_1/HC-SR04 (2–400 cm),
HABITACION_2/LDR (enteros 0–4095). evento es opcional (LECTURA).
luz es opcional y debe ser booleano; se recomienda enviarlo en cada lectura.
Eventos aceptados: PRESENCIA, SIN_PRESENCIA, MUY_CERCA, OSCURIDAD, OSCURO,
CLARO, LUZ_SUFICIENTE, LUZ_ENCENDIDA, LUZ_APAGADA, ENCENDER_LUZ,
APAGAR_LUZ, LECTURA, IRQ_PIR.

Clasificación: distancia con umbrales de 30 y 100 cm; LDR con histéresis
2000 ± 150 y oscuridad con valores altos. El control de actuadores y los
temporizadores siguen en el firmware. El firmware actual todavía necesita
que su responsable agregue MQTT y el manejo de comandos.

Opciones: --puerto 8000, --datos backend/datos, --puerto-mqtt 1883,
--tls (usar --puerto-mqtt 8883 si corresponde).
Variables de entorno: SLS_MQTT_HOST, SLS_MQTT_PREFIJO, SLS_MQTT_USUARIO,
SLS_MQTT_PASSWORD. No guardar credenciales en código.
La API es local y no tiene autenticación; para publicarla hay que configurar
acceso y HTTPS en la infraestructura.

## Persistencia y pruebas

CSV por lectura y JSON mediante reemplazo temporal. Al reiniciar, el CSV
reconstruye el estado aunque el JSON haya quedado pendiente. Ejecutar una
sola instancia por directorio de datos. Mensajes duplicados se registran
nuevamente; no hay deduplicación MQTT.

```powershell
python -m unittest backend.test_backend -v
```

La prueba con broker real y ESP32 queda pendiente de la plataforma elegida
y de la implementación MQTT del firmware.
