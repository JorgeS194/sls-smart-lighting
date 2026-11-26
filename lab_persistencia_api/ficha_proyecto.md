# Ficha del proyecto SLS (Parte A)

**Proyecto:** Smart Lighting System (SLS) — casa inteligente con ESP32, sensor PIR (Sala), HC-SR04 (Habitación 1) y LDR (Habitación 2).

## 1. JSON que publica el dispositivo

```json
{"zona": "SALA", "distancia_cm": 45.5, "luz_adc": 2150, "movimiento": 1, "luz_encendida": 1}
```

## 2. Campos

| Campo | Tipo | Obligatorio | Rango o valores permitidos | Por qué ese límite |
|---|---|---|---|---|
| zona | texto | Sí | texto libre (no vacío) | Nombre de la zona que reporta (SALA, HABITACION_1, HABITACION_2). Es libre para poder probar la inyección SQL. |
| distancia_cm | real | No | 2 a 400 | Rango físico del HC-SR04. Es opcional porque sin eco el sensor no da lectura y no se inventa un cero. |
| luz_adc | entero | Sí | 0 a 4095 | El ADC del ESP32 es de 12 bits: no puede dar nada fuera de ese rango. |
| movimiento | entero | Sí | 0 o 1 | El PIR solo dice "hay" o "no hay" movimiento. |
| luz_encendida | entero | Sí | 0 o 1 | La luz de la zona está apagada (0) o encendida (1). |

## 3. Campo principal

`luz_adc`: es el número que se resume (mínimo, máximo y promedio por hora). Muestra cómo cambia la luz ambiental durante el día, que es lo que el SLS usa para decidir si enciende la luz.

## 4. Datos del proyecto.py

- Tabla: `telemetria_sls`
- Tema MQTT: `utp/ds8/USUARIO/sls/telemetria` (estado en `utp/ds8/USUARIO/sls/estado`)
- Base de datos: `proyecto.db`

## 5. Comprobación

`python -c "import proyecto"` no muestra ningún mensaje: la ficha pasó la comprobación.
