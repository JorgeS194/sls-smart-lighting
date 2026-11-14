# Contrato de integración · paso 1

Base: backend de Abrahan, PR #9. Este cambio es aditivo y no modifica el firmware,
el circuito, los comandos existentes ni el diseño del dashboard del PR #12.

Rama local: `fix/backend-francesco-contrato-firmware`.
Base del futuro PR: `feat/backend-api-mqtt` (PR #9).
Título propuesto: `fix(backend): admite eventos del firmware sin alterar lecturas`.
No se publica ni se integra en otras ramas en este paso.

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
- Publicar un comando no demuestra ejecución física; esa parte queda fuera de
  la demostración acordada de Etapa 3.

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
