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

`actuador_ventilador.py`, `red.py` y `mensajes.py` son módulos previstos para la Etapa 3.

## Subir a la placa física (ejemplo)
```bash
mpremote connect COM3 fs cp main.py :main.py
```
Cambia `COM3` por el puerto de tu placa.
