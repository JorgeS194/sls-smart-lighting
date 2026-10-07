# tools/

Herramientas de apoyo que no forman parte del sistema final.

## simulacion_sensores.py (Etapa 2)
Simulación en Python (PC) de tres sensores (PIR, HC-SR04 y LDR) con clasificación de lecturas, eventos, manejo de excepciones, estado en JSON y exportación del historial a CSV.

```bash
python tools/simulacion_sensores.py --ciclos 40 --pausa 0 --semilla 7
```

Escribe `estado.json` e `historial.csv` en la carpeta desde donde se ejecuta.

## Evolución prevista
En la Etapa 3 sus partes de JSON, CSV y excepciones pasan al `backend/`, y su generador de lecturas pasa a `tools/dispositivo_falso.py`: publica datos de mentira para probar el backend sin abrir Wokwi.
