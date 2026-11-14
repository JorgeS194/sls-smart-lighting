# Contrato MQTT propuesto · Avance 3

Este documento define la implementación objetivo. El PR #13 aporta compatibilidad
con eventos individuales; todavía no implementa el contrato nuevo ni acredita
una conexión real. La orden remota es obligatoria según la guía del Avance 3.

## Tópicos e identidad

Base del dispositivo: `utp/ds8/<grupo>/<proyecto>/<dispositivo>`. Ejemplo:
`utp/ds8/1gs133/sls-smart-lighting/casa-01`. Confirmar el identificador del
grupo antes del ensayo. Usar segmentos sin espacios, `/`, `+` ni `#`.

| Tópico bajo la base | Dirección | Contenido | QoS | Retenido |
|---|---|---|---|---|
| `telemetria` | Dispositivo → broker → receptor | Instantánea de sensores y luces | 1 | No |
| `estado` | Dispositivo o Last Will del broker → receptor | Disponibilidad `online` u `offline` | 1 | Sí |
| `comandos` | Backend o herramienta de prueba → broker → dispositivo | Orden sobre una zona | 1 | No |

El receptor se suscribe a `utp/ds8/<grupo>/<proyecto>/+/telemetria` y
`utp/ds8/<grupo>/<proyecto>/+/estado`. Enruta según tópico y comprueba que
el identificador del mensaje coincida con el segmento del dispositivo. El
ESP32 escucha únicamente su tópico `comandos` y vuelve a suscribirse al reconectar.

## Telemetría periódica

Propuesta: publicar cada 2 segundos, aunque las lecturas no cambien. PIR y LDR
son obligatorios para aportar dos lecturas por mensaje. Distancia es opcional;
`null` indica ausencia de eco o lectura fuera del rango aceptado, nunca cero ficticio.

```json
{"version":2,"dispositivo":"casa-01","sesion":"demo-01","secuencia":1,"intervalo_ms":2000,"lecturas":{"pir":0,"ldr_adc":2593,"distancia_cm":60},"luces":{"SALA":false,"HABITACION_1":true,"HABITACION_2":true}}
```

- `pir`: entero `0` o `1`; `ldr_adc`: entero de `0` a `4095`. No aceptar booleanos como números.
- `distancia_cm`: número finito entre `2` y `400`, o `null`.
- `luces`: booleanos por zona canónica, según el estado aplicado por el controlador.
- `sesion`: identificador nuevo por arranque; `secuencia`: entero positivo creciente dentro de la sesión.
- `intervalo_ms`: entero positivo; configurar el monitor con el mismo intervalo nominal.

El receptor valida la instantánea completa antes de guardar. Registra una fila
por lectura válida en el CSV con encabezado y conserva la API de Abrahan. Los
eventos individuales del #13 mantienen su formato legado y no cuentan como
instantáneas periódicas para el monitor. La deduplicación persistente por
dispositivo, sesión y secuencia podrá añadirse por separado.

## Disponibilidad y monitor

```json
{"version":2,"dispositivo":"casa-01","sesion":"demo-01","estado":"online"}
```

Configurar antes de conectar un Last Will con la misma sesión y `estado: "offline"`.
Publicar `online` retenido tras conectar. El monitor Python distingue `ONLINE`
al recibir telemetría válida reciente, `SIN_DATOS` cuando el dispositivo sigue
disponible pero supera el silencio permitido, y `OFFLINE` al recibir el testamento.
Antes de tener evidencia, mostrar estado desconocido en la interfaz; no confundir
la caída del receptor con un testamento del dispositivo. Una sesión antigua no
debe sobrescribir una nueva ya observada.

Silencio configurable: 8 segundos para el ejemplo de 2 segundos de publicación;
debe ser al menos tres veces el intervalo. Medir desde la última instantánea
válida de la sesión, o desde `online` mientras espera la primera. Los latidos y
eventos individuales no reinician ese reloj. Registrar solo transiciones en
`comunicaciones.csv` con encabezado `fecha,tipo,gravedad,detalle`.

## Órdenes y recuperación

```json
{"id":"cmd-01","zona":"SALA","accion":"apagar"}
```

Conservar el formato de órdenes del backend: identificador, zona canónica y
acción. La primera implementación admitirá `apagar` y `auto`: el primero mantiene
apagada la zona en modo manual; el segundo restablece su control automático.
Rechazar tipos, zonas o acciones no soportadas en consola, sin cambiar el estado.
Aplicar las órdenes desde el ciclo de control; el hilo MQTT solo las entrega.
Confirmar el resultado con las luces observadas en la siguiente telemetría.

Durante una caída, conservar el control local y reintentar con esperas crecientes
acotadas (propuesta: 2 a 60 segundos). Al recuperar, volver a anunciar estado,
suscribirse y publicar una instantánea fresca. Para un broker público, usar solo
datos ficticios y ninguna credencial real; un prefijo propio evita cruces
accidentales, pero no proporciona autenticación ni control de acceso.

## PR siguientes

1. Publicación periódica del firmware; preservar eventos y control local.
2. Recepción de instantáneas y suscripción con comodines en el backend.
3. Disponibilidad retenida y Last Will del dispositivo.
4. Recepción y ejecución de órdenes en el ESP32.
5. Reintentos crecientes del firmware.
6. Monitor Python y CSV de transiciones.
7. Dashboard sobre la API compartida.
8. Pruebas integrales en Wokwi y evidencia de los ocho escenarios de la guía.
9. Informe y ensayo de la demostración.

## Compatibilidad previa (PR #13)

Base: backend de Abrahan, PR #9. Este cambio es aditivo y no modifica el firmware,
el circuito, los comandos existentes ni el diseño del dashboard del PR #12.


## Compatibilidad de mensajes

El backend conserva sus identificadores `SALA`, `HABITACION_1`, `HABITACION_2`.
También acepta `HABITACION 1` y `HABITACION 2` del firmware y normaliza su nombre.

Las lecturas siguen siendo números válidos para PIR, HC-SR04 y LDR. Los eventos
de presencia y encendido/apagado pueden llevar `valor: ""` o `null`, porque no
siempre incluyen una lectura nueva. No se inventa ni reemplaza el último valor
numérico. Antes de la primera lectura, ese valor permanece `null`.

`IRQ_PIR` admite un contador entero positivo: se conserva en el historial pero
no se interpreta como nivel binario del PIR ni cambia su clasificación.
CSV guarda los valores ausentes como campo vacío y los reconstruye como `null`.
Los CSV anteriores, con lecturas numéricas, mantienen su compatibilidad.

El campo opcional `version` solo acepta el entero `1`. El backend aún no utiliza
los metadatos dispositivo/sesión/secuencia para deduplicación; eso requiere otro
cambio. Los latidos no son lecturas de zona y no deben enviarse a telemetría.

## Contratos que se conservan del PR #9

- MQTT de entrada: `<prefijo>/telemetria`; salida de comandos: `<prefijo>/comandos`.
- API: `/api/salud`, `/api/estado`, `/api/historial`, `/api/lecturas`, `/api/comandos`.
- Publicar un comando no demuestra ejecución física; debe verificarse en el ESP32.

## Validación y siguientes cambios

```bash
python -m unittest backend.test_backend backend.test_contrato_firmware -v
```

Este paso prueba recepción, normalización, procesamiento e historial/reinicio.
Resultado local: 14 pruebas correctas (5 originales y 9 de compatibilidad).
Además se ejecutó el banco `tests/prueba_main.py` de la copia del PR #12 con
un colector local: sus 16 mensajes JSON, generados por `mensajes.py`, fueron
aceptados por este backend; las tres luces terminaron apagadas y el estado se
reconstruyó correctamente desde CSV al reiniciar. No fue una prueba en Wokwi
ni utilizó un broker: verifica el contrato y procesamiento, no la conexión real.

Todavía falta adaptar el dashboard a esta API y alinear el tópico del firmware,
configurar el broker expresamente y validar Wokwi → MQTT → backend → dashboard.
Cada uno se prepara por separado. No se conecta ningún servicio externo ni
se modifica el PR #9 automáticamente.
