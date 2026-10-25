# firmware/

Código MicroPython del ESP32. **Esta carpeta es plana a propósito**: Wokwi web mantiene los archivos en un solo nivel, así que lo que hay aquí se pega tal cual en Wokwi y se copia igual a la placa física. Los módulos se distinguen por prefijo (`sensor_`, `actuador_`), no por subcarpeta.

## Estado actual
- El firmware ya está dividido en módulos, con la lógica y los umbrales de la Etapa 2. `main.py` coordina sensores y controlador; `zonas.py` guarda el estado, `logica.py` decide, `controlador.py` aplica eventos y `historial.py` registra en RAM con escritura CSV comentada. Copia todos los `.py` al mismo nivel en Wokwi o la placa.

## Módulos actuales y previstos
| Archivo | Contenido |
|---|---|
| `main.py` | Solo el ciclo principal (orquesta) |
| `config.py` | `ENTORNO` ("wokwi" / "real"), pines, umbrales, tiempos, tópicos MQTT |
| `secrets_example.py` | Plantilla de credenciales. El `secrets.py` real **no se sube** |
| `logica.py` | Clasificación, histéresis y decisiones que actualizan el estado (sin `machine`) |
| `zonas.py` | Estado de Sala, Habitación 1 y Habitación 2 |
| `controlador.py` | Ejecuta eventos: LEDs, consola e historial |
| `historial.py` | Registro en RAM y CSV opcional para placa real |
| `sensor_pir.py` | PIR e interrupción |
| `sensor_ultrasonico.py` | HC-SR04 |
| `sensor_ldr.py` | LDR |
| `actuador_leds.py` | 74HC595 |
| `actuador_ventilador.py` | Servo (Wokwi) / motor 5V con driver (real) |
| `red.py` | WiFi, MQTT y reintentos (Etapa 3) |
| `mensajes.py` | Arma el JSON de cada mensaje |

Regla: después de **cada** corte de módulo se prueba en Wokwi que el comportamiento sea idéntico antes de seguir.

`red.py` y `mensajes.py` ya están implementados; la comunicación está desactivada
por defecto. `actuador_ventilador.py` sigue previsto para la Etapa 3.

## WiFi, MQTT y JSON (Etapa 3)

Estado inicial seguro: `HABILITAR_RED = False` y `MQTT_SERVIDOR = ""` en
`config.py`. Así se ejecuta únicamente el control local, igual que antes.
No se publica nada hasta elegir un destino, configurarlo y habilitar la red.

1. Copia todos los `.py` de esta carpeta al mismo nivel en Wokwi.
2. Comprueba primero PIR, HC-SR04, LDR y apagado temporizado con la red desactivada.
3. Para una prueba de comunicación, configura el broker elegido y su puerto en
   `config.py`; usa un `MQTT_PREFIJO` propio y un `MQTT_DISPOSITIVO` distinto por placa.
4. Wokwi usa `WIFI_SSID = "Wokwi-GUEST"` y contraseña vacía. Para la placa real,
   copia `secrets_example.py` como `secrets.py`, completa las credenciales allí
   y cambia `ENTORNO = "real"`. No subas ese archivo.
5. Hace falta `umqtt.simple`. Wokwi ofrece esta biblioteca; si la imagen no la
   incluye, instala el paquete oficial en la placa con `mip.install("umqtt.simple")`
   después de conectarla a WiFi. No se instala con `pip` del PC.
6. Abre un suscriptor MQTT antes de arrancar; reemplaza `BROKER_ELEGIDO`:

   ```bash
   mosquitto_sub -h BROKER_ELEGIDO -p 1883 -t "utp-sls/jorge-s194/casa-01/#" -v -q 1
   ```

7. Activa `HABILITAR_RED = True` y reinicia. Debes ver `[RED] Conectando WiFi`
   y después `[RED] MQTT conectado: .../eventos`. Activa cada sensor y comprueba
   los mensajes del suscriptor. Guarda consola y mensajes como evidencia.

La implementación actual es MQTT sin autenticación ni TLS. Para uso real con
un broker privado hay que incorporar esos parámetros y verificar certificados;
no introduzcas contraseñas reales del broker en esta versión. Un broker público
solo sería adecuado para una demostración autorizada con lecturas ficticias.

### Funcionamiento y límites

- `main.py` inicia una sola tarea con `_thread`. Solo esa tarea toca WiFi/sockets;
  el ciclo principal encola los eventos después del control local. No se modifican
  los umbrales, la histéresis, los pines ni los temporizadores.
- Se reintenta cada 5 segundos tras un fallo; WiFi tiene un plazo de 15 segundos.
  La cola conserva hasta 50 eventos. Si se llena, descarta el más viejo y cuenta
  los descartes. No persiste entre reinicios ni promete conservar toda una caída larga.
- Se publica un evento por vuelta del hilo con QoS 1, sin retención. Solo se retira
  de la cola al confirmarse el envío. Una confirmación perdida puede producir
  duplicados: el backend deberá deduplicar por dispositivo, sesión y secuencia.
- `.../conexion` publica un `LATIDO` al conectar y tras 10 segundos sin envíos.
  Sirve para mantener la sesión MQTT; no es una instantánea de las luces ni un
  estado retenido. Todavía no se reciben comandos remotos.
- `umqtt.simple` reciente admite `connect(timeout=...)`; para las versiones antiguas
  se usa `connect()` en el hilo de red. DNS y ciertas esperas internas de esa
  biblioteca pueden tardar más que el timeout. Esto no detiene el hilo de sensores,
  pero puede retrasar la reconexión. Debe verificarse con la imagen real de Wokwi.
- MicroPython considera `_thread` experimental. Las pruebas de CPython verifican
  la separación y la cola; aún hace falta validar el hilo en Wokwi y en la placa.
- Si faltan los módulos de red o no puede crearse el hilo, se informa en consola
  y continúa el control local.

### Contrato JSON v1

Tópico de eventos: `<prefijo>/<dispositivo>/eventos`.

```json
{"version":1,"dispositivo":"casa-01","sesion":"a1b2c3d4","secuencia":1,"tiempo_ms":960,"zona":"HABITACION 1","sensor":"HC-SR04","evento":"PRESENCIA","valor":95,"luz":true}
```

Sensores: `SALA` → `PIR`, `HABITACION 1` → `HC-SR04`, `HABITACION 2` → `LDR`.
Eventos: `IRQ_PIR`, `PRESENCIA`, `SIN_PRESENCIA`, `OSCURIDAD`, `LUZ_SUFICIENTE`,
`LUZ_ENCENDIDA`, `LUZ_APAGADA`. `valor` es un número cuando existe una lectura
asociada, o `""` cuando no aplica. `luz` refleja el estado local de la zona al
encolar. `tiempo_ms` es el contador del ESP32, no una fecha UTC; el backend pondrá
fecha de recepción. Sesión y secuencia se reinician en cada arranque de la red.

Referencias: [WiFi de Wokwi](https://docs.wokwi.com/guides/esp32-wifi),
[umqtt.simple oficial](https://github.com/micropython/micropython-lib/tree/master/micropython/umqtt.simple),
[`_thread` de MicroPython](https://docs.micropython.org/en/latest/library/_thread.html).

## Subir a la placa física (ejemplo)
```bash
mpremote connect COM3 fs cp main.py :main.py
```
Cambia `COM3` por el puerto de tu placa.
