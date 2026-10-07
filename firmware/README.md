# firmware/

Código MicroPython del ESP32. **Esta carpeta es plana a propósito**: Wokwi web mantiene los archivos en un solo nivel, así que lo que hay aquí se pega tal cual en Wokwi y se copia igual a la placa física. Los módulos se distinguen por prefijo (`sensor_`, `actuador_`), no por subcarpeta.

## Estado actual
- `main.py`: versión entregada en la Etapa 2, **sin dividir** (misma lógica, mismos umbrales). Incluye sensores PIR (con interrupción), HC-SR04 y LDR, control de LEDs por 74HC595 y registro de eventos con escritura a CSV comentada.

## Plan de división en módulos
| Archivo | Contenido |
|---|---|
| `main.py` | Solo el ciclo principal (orquesta) |
| `config.py` | `ENTORNO` ("wokwi" / "real"), pines, umbrales, tiempos, tópicos MQTT |
| `secrets_example.py` | Plantilla de credenciales. El `secrets.py` real **no se sube** |
| `logica.py` | Funciones puras: histéresis, clasificación (sin `machine`) |
| `sensor_pir.py` | PIR e interrupción |
| `sensor_ultrasonico.py` | HC-SR04 |
| `sensor_ldr.py` | LDR |
| `actuador_leds.py` | 74HC595 |
| `actuador_ventilador.py` | Servo (Wokwi) / motor 5V con driver (real) |
| `red.py` | WiFi, MQTT y reintentos (Etapa 3) |
| `mensajes.py` | Arma el JSON de cada mensaje |

Regla: después de **cada** corte de módulo se prueba en Wokwi que el comportamiento sea idéntico antes de seguir.

## Subir a la placa física (ejemplo)
```bash
mpremote connect COM3 fs cp main.py :main.py
```
Cambia `COM3` por el puerto de tu placa.
