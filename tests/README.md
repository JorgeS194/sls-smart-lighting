# tests/

## prueba_main.py
Banco de pruebas que ejecuta `firmware/main.py` en Python normal usando un ESP32 simulado (reloj, pines, ADC y sensor ultrasónico falsos). Comprueba que la lógica de las zonas funciona, que la interrupción del PIR se atiende y que el bloque de CSV, al descomentarlo, genera `historial.csv`.

```bash
python tests/prueba_main.py
```

No sustituye la prueba en Wokwi: sirve para detectar regresiones rápido después de tocar el firmware.

## prueba_red.py

Pruebas de Etapa 3 con WiFi y broker falsos, sin conexiones externas ni paquetes
adicionales de Python:

```bash
python -m unittest discover -s tests -p prueba_red.py -v
```

Verifica el contrato JSON y tipos de lecturas, conexión WiFi, timeout y reintento,
broker caído, rechazo MQTT, reenvío en orden, cola acotada y descarte concurrente,
latidos y arranque de un solo hilo. Además ejecuta `main.py` con WiFi ausente,
broker caído y broker conectado, y compara todos los eventos y tiempos locales
con la ejecución sin red. Una prueba mantiene un envío bloqueado y confirma
que el productor puede seguir encolando sin esperar al socket.

La prueba usa hilos de CPython y un transporte simulado; no acredita conectividad
real ni compatibilidad del hilo con una versión concreta de MicroPython.
Validar en Wokwi con la red desactivada y luego activada, suscriptor MQTT abierto;
capturar recepción de JSON y control de luces. Para caídas, probar WiFi ausente
o un broker inaccesible y confirmar que los sensores y LEDs siguen respondiendo.

## Dashboard y backend

```bash
node --test tests/test_dashboard.mjs
python -m unittest discover -s tests -p test_backend_dashboard.py -v
```

El modelo comprueba demo, estados vacíos, filtros, CSV, escape HTML y sesiones.
El backend usa SQLite temporal y HTTP local para verificar importación,
validación, persistencia, deduplicación, exportación y archivos servidos.
No contacta brokers externos.

## Convención
- Un archivo por área: `test_firmware_*.py`, `test_backend_*.py`.
- Cada prueba indica el requerimiento que verifica (RF-xx / RNF-xx) para alimentar la tabla de verificación del informe final.
