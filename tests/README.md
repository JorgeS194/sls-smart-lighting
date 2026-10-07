# tests/

## prueba_main.py
Banco de pruebas que ejecuta `firmware/main.py` en Python normal usando un ESP32 simulado (reloj, pines, ADC y sensor ultrasónico falsos). Comprueba que la lógica de las zonas funciona, que la interrupción del PIR se atiende y que el bloque de CSV, al descomentarlo, genera `historial.csv`.

```bash
python tests/prueba_main.py
```

No sustituye la prueba en Wokwi: sirve para detectar regresiones rápido después de tocar el firmware.

## Convención
- Un archivo por área: `test_firmware_*.py`, `test_backend_*.py`.
- Cada prueba indica el requerimiento que verifica (RF-xx / RNF-xx) para alimentar la tabla de verificación del informe final.
