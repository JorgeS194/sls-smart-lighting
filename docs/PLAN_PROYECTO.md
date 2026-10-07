# Plan del proyecto – SLS Smart Lighting System

Documento de referencia del equipo: qué decidimos, cómo está organizado el repositorio, quién hace qué y en qué orden. Se alinea con la guía del curso y con el cronograma de la Etapa 1.

---

## 1. Decisiones de arquitectura

| Tema | Decisión | Por qué |
|---|---|---|
| Qué hace el ESP32 | Solo hardware: lee sensores, decide y controla las luces, y **envía datos**. | La guía separa firmware (MicroPython) de backend (Python 3). |
| Dónde se procesa y guarda | En el **backend** (Python 3): valida, procesa, genera `estado.json` e `historial.csv`. | JSON/CSV y la nube pertenecen a Python y a "persistencia y servicios remotos", no al microcontrolador. |
| Cómo viajan los datos | **MQTT por WiFi** (Etapa 3), con JSON. | La guía exige "Wokwi → servidor o broker (HTTP o MQTT)". MQTT va en ambos sentidos, así que también sirve para mandar comandos desde el panel. |
| Cómo se muestra | **Dashboard** web que habla con el backend/broker, **no** directamente con el ESP32. | El gateway público de Wokwi solo permite conexiones salientes; un servidor web dentro del ESP32 no se podría demostrar en Wokwi. |
| Código para Wokwi y placa real | **Un solo código fuente.** Solo cambian `config.py` y los adaptadores de hardware. | Evita mantener dos proyectos y la duplicación que la rúbrica penaliza. |
| Estructura de `firmware/` | **Plana** (sin subcarpetas). | Wokwi web mantiene los archivos en un solo nivel. |
| Luces sin internet | El control de luces **sigue funcionando** si se cae el WiFi. | Confiabilidad: la red es para monitoreo y comandos, no para decidir. |

### Ajuste respecto a la propuesta de la Etapa 1
La propuesta describía un "servidor web integrado" en el ESP32. Se cambia por **ESP32 → broker MQTT → backend → dashboard**, porque (a) la guía de la Etapa 3 pide enviar datos desde el dispositivo a un servidor o broker, y (b) Wokwi, con su gateway público, no admite conexiones entrantes. La funcionalidad "consultar el estado y sobrescribir el control" se mantiene, con comandos bidireccionales por MQTT. **Este ajuste hay que comunicárselo al profesor como una decisión de diseño justificada.**

## 2. Cómo funciona (ejemplo completo)

Alguien entra a la sala:

1. El PIR sube a 1 y salta la **interrupción**: la rutina (ISR) solo levanta una bandera.
2. El ciclo del ESP32 ve la bandera, enciende el LED de la Sala y reinicia el temporizador de 5 s. **No depende de internet.**
3. El ESP32 arma un JSON, por ejemplo `{"zona":"SALA","sensor":"PIR","valor":1,"evento":"PRESENCIA"}`, y lo publica al broker.
4. El backend lo recibe y lo **valida**. Si llega roto, la excepción se captura y el programa sigue.
5. Actualiza `estado.json` (cómo está la casa ahora) y agrega una fila a `historial.csv` (todo lo que pasó).
6. El dashboard muestra el cambio. Si el usuario pulsa "apagar sala", el comando viaja en sentido contrario y el ESP32 lo ejecuta.

**Si falla la conexión:** `red.py` reintenta y guarda los mensajes pendientes en una cola corta para enviarlos al reconectar (manejo básico de fallos que pide la Etapa 3). El ESP32 no conoce la hora real, así que el backend pone la fecha al recibir.

```
 Sensores y LEDs ──▶ ESP32 (firmware) ──WiFi──▶ Broker MQTT ──▶ Backend (Python) ──▶ Dashboard
                          ▲                                            │
                          └─────────────── comandos ◄──────────────────┘
```

**Qué pasa con lo de la Etapa 2:** la interrupción, la histéresis y el temporizador de 5 s siguen en el firmware. El JSON, el CSV y las excepciones pasan al backend. `tools/simulacion_sensores.py` se convierte en `tools/dispositivo_falso.py`, un publicador de datos de mentira para probar el backend sin abrir Wokwi.

## 3. Estructura objetivo del repositorio

```
sls-smart-lighting/
├── README.md
├── .gitignore
├── .github/pull_request_template.md
│
├── firmware/                    # PLANO: igual que Wokwi
│   ├── main.py                  # solo el ciclo principal
│   ├── config.py                # ENTORNO ("wokwi"/"real"), pines, umbrales, tópicos
│   ├── secrets_example.py       # plantilla; secrets.py real NO se sube
│   ├── logica.py                # funciones puras: histéresis, clasificación
│   ├── sensor_pir.py            # PIR + interrupción
│   ├── sensor_ultrasonico.py
│   ├── sensor_ldr.py
│   ├── actuador_leds.py         # 74HC595
│   ├── actuador_ventilador.py   # servo (Wokwi) / motor (real)
│   ├── red.py                   # WiFi + MQTT + reintentos
│   └── mensajes.py              # arma el JSON de cada mensaje
│
├── backend/                     # Python 3
│   ├── requirements.txt
│   ├── main.py
│   ├── receptor.py              # recibe y valida (excepciones)
│   ├── procesamiento.py         # eventos, estado de la casa
│   ├── persistencia.py          # estado.json, historial.csv
│   └── datos/                   # salidas (ignorado por git)
│
├── dashboard/                   # panel de monitoreo y control
├── tools/dispositivo_falso.py   # antes: simulacion_sensores.py
├── tests/
├── wokwi/                       # diagram.json y enlace
└── docs/                        # informe, diagramas, RF/RNF, bitácora
```

**Lo que cambia entre Wokwi y la placa real** vive solo aquí:

```python
# config.py
ENTORNO = "wokwi"          # cambia a "real" en la placa física
if ENTORNO == "wokwi":
    WIFI_SSID, WIFI_PASS = "Wokwi-GUEST", ""
    PIN_VENTILADOR = 18
else:
    from secrets import WIFI_SSID, WIFI_PASS   # no se sube a GitHub
    PIN_VENTILADOR = 25
```

`main.py` solo llama a `ventilador.encender()`; el archivo `actuador_ventilador.py` mueve un servo en Wokwi o activa el driver del motor en la placa real, y el resto del código no se entera.

## 4. Roles y responsabilidades

| Rol (Etapa 1) | Carpetas | Responsabilidad en las próximas etapas |
|---|---|---|
| **Líder / Firmware** | `firmware/`, `wokwi/` | Partir `main.py` en módulos, `red.py` (WiFi, MQTT, reintentos), ventilador, circuito de Wokwi y montaje físico; coordina entregas y administra el repo. |
| **Desarrolladores web (2)** | `backend/`, `dashboard/` | Uno de ellos lleva el backend (receptor, validación, persistencia, nube) y el otro el dashboard (panel, comandos). Se rotan la revisión del trabajo del otro. |
| **QA y Documentación** | `tests/`, `docs/` | Numerar RF/RNF, matriz de pruebas con escenarios límite, evidencia, informe por etapas, bitácora. |

Reglas de equipo: ver [`GUIA_GITHUB.md`](GUIA_GITHUB.md).

## 5. Plan por semanas (alineado con el cronograma de la Etapa 1)

| Cuándo | Qué | Quién |
|---|---|---|
| **Paso 0** (1–2 h, todos juntos) | Crear repo **privado**, dar acceso al profesor, subir esta estructura, etiqueta `etapa-2`, activar protección de `main`. **Sin cambiar lógica.** Comprobar que Wokwi sigue corriendo igual. | Todos |
| **Semana 9** | Partir `main.py` en módulos probando en Wokwi tras cada corte. En paralelo, **spike de MQTT**: la placa publica "hola" y el backend lo recibe. Borrador de RF/RNF. | Firmware / Backend / QA |
| **Semana 10** | Mensajes JSON reales. Backend que valida y guarda (`estado.json`, `historial.csv`). Ventilador con servo. Primer dashboard. | Todos |
| **Semana 11** | Reintentos y cola de envío. Plataforma en la nube. Pruebas de escenarios límite. | Firmware / QA / Backend |
| **Semana 12** | Pulido, ensayo de la demo y **entrega de la Etapa 3**. Etiqueta `etapa-3`. | Todos |
| **Semanas 13–14** | Pruebas de integración y optimización. Extras (si aplica). Congelado de funcionalidades al final de la 14. | Todos |
| **Semanas 15–16** | Informe final, guía de usuario, ensayo de la presentación oral (15 min, todos participan). | Todos |

### Decisiones pendientes (esta semana)
1. **Plataforma en la nube** (la guía exige conectarse a una "plataforma en la nube elegida" para la demo).
2. **Broker MQTT**. Un broker público sirve para empezar, pero no tiene privacidad: usar un prefijo único en los tópicos (por ejemplo `utp-sls-g3/...`).
3. **¿Qué dispara el ventilador?** Hoy no hay un sensor que lo justifique; un DHT22 (temperatura) encaja de forma natural y existe en Wokwi.

## 6. Diferencias Wokwi vs. hardware real (cosas que Wokwi perdona)

- **Motor de 5 V:** nunca conectado directo a un GPIO. Necesita un relé, o un transistor/MOSFET con diodo de protección, y **tierra común**. Revisar la corriente de arranque (puede reiniciar el ESP32 si comparte la alimentación).
- **ECHO del HC-SR04:** entrega 5 V y los pines del ESP32 no los toleran. En la placa real hace falta un divisor de voltaje.
- **GPIO12:** es un pin de arranque (*strapping*) del ESP32; con ECHO ahí puede causar problemas al encender. En el real conviene otro pin, por eso los pines van en `config.py`.
- **PIR real:** tarda unos segundos en estabilizarse al encender y tiene sus potenciómetros de sensibilidad y tiempo.
- **LDR real:** hay que calibrar el umbral (`UMBRAL_LUZ`, `OSCURO_ES_VALOR_ALTO`) con `DEPURAR_LDR = True`.

## 7. Proceso para los extras: puerta móvil y cámara de videovigilancia

> **Los extras son secundarios.** Primero se cumple todo lo que pide el profesor en cada etapa. Estos pasos solo aplican cuando la etapa vigente está en `main`, probada y etiquetada.

### 7.1 Puerta móvil controlada por sensor ultrasónico

**Idea:** un HC-SR04 detecta que alguien se acerca (menos de X cm) y un servo abre la puerta; después de T segundos sin presencia, la cierra. Es el mismo patrón que la Habitación 1 (presencia por distancia + temporizador), con un actuador distinto.

**Pasos**
1. **Mini-especificación (QA, 1 página):** requisitos extra con criterio de aceptación, por ejemplo `RF-E01: la puerta se abre cuando una persona está a menos de X cm`, `RF-E02: la puerta no se cierra mientras haya alguien en el umbral`, `RNF-E01: responde en menos de 1 s`.
2. **Issue + milestone `Extras`** con etiqueta `extra` y rama `feat/extra-puerta-...`.
3. **Diseño (líder + backend):** tópicos MQTT (por ejemplo `.../puerta/estado` con `abierta/cerrada/abriendo`, y `.../puerta/cmd` con `abrir/cerrar/auto`) y formato del JSON.
4. **Firmware (líder):** `sensor_puerta.py` y `actuador_puerta.py` (servo con PWM a 50 Hz), reutilizando `logica.py`. En `config.py`: `HABILITAR_PUERTA = False` por defecto. Pines nuevos: evitar GPIO12 y usar solo entradas para ECHO.
5. **Wokwi:** segundo HC-SR04 y un segundo servo. Si el circuito base se vuelve confuso, ordenar y etiquetar.
6. **Backend (web 1):** guardar los eventos de la puerta en `estado.json` / `historial.csv` y exponer el comando.
7. **Dashboard (web 2):** estado de la puerta y botón de apertura/cierre manual.
8. **Pruebas (QA):** escenarios límite: persona que se queda en el umbral, lecturas sin eco, comando manual durante el cierre, pérdida de WiFi.
9. **Hardware real:** servo con alimentación adecuada (los picos de corriente pueden reiniciar el ESP32 si comparte la fuente) y tierra común.
10. **Documentación (QA):** sección "Funcionalidades adicionales" del informe y el guion de la demo.

### 7.2 Cámara de videovigilancia

Es el extra **más pesado**; se recomienda hacer primero la puerta. Se propone en dos niveles:

| Nivel | Qué es | ¿Funciona en Wokwi? |
|---|---|---|
| **1. Alerta de vigilancia** (software) | Modo "armado" activable desde el dashboard. Si hay presencia con el modo armado, se genera el evento `VIGILANCIA_MOVIMIENTO` con zona y hora; el dashboard muestra la alerta y una imagen de ejemplo (*placeholder*). | Sí: se basa en los sensores que ya existen. |
| **2. Cámara real** (hardware) | Módulo de cámara (por ejemplo, un ESP32-CAM) como dispositivo aparte, que entrega fotos o *streaming*; el dashboard enlaza o incrusta la imagen. | No se podría demostrar desde Wokwi (no lo he verificado; revisar la lista de componentes). Se muestra en la placa real o en un video. |

**Cosas a tener en cuenta**
- La cámara real es **otra placa con su propio firmware**, y normalmente se programa en Arduino/C++ más que en MicroPython. Es una carga adicional de trabajo, no una línea más en el firmware actual.
- El *streaming* implica conexiones **entrantes** a la cámara (no viable desde Wokwi) y mucho ancho de banda.
- **Privacidad:** grabar o transmitir personas requiere consentimiento. Para la demostración, usar solo a los integrantes del equipo.

**Pasos** (mismo proceso que la puerta)
1. Mini-especificación con RF-E del nivel 1; el nivel 2 queda como "trabajo futuro / demostración real".
2. Issue, milestone `Extras`, rama `feat/extra-vigilancia-...`, bandera `HABILITAR_VIGILANCIA = False`.
3. Diseño del mensaje de alerta y del modo armado (`.../vigilancia/cmd`: `armar/desarmar`).
4. Backend: guarda alertas con fecha; endpoint para listarlas.
5. Dashboard: interruptor de modo armado y lista de alertas con imagen.
6. Pruebas: modo desarmado no genera alertas, alerta duplicada, WiFi caído (cola).
7. Nivel 2, solo si sobra tiempo: prueba de concepto con la placa de cámara y video de respaldo.

### 7.3 Reparto de roles en los extras

| Rol | Puerta | Cámara |
|---|---|---|
| Líder / Firmware | Sensor y actuador de la puerta, Wokwi, montaje físico | Lógica de alerta en firmware; placa de cámara (nivel 2) |
| Web (backend) | Tópicos, persistencia y comandos de la puerta | Almacenar alertas, endpoint |
| Web (dashboard) | Estado y control de la puerta | Modo armado, lista de alertas, imagen |
| QA y Documentación | RF-E, pruebas límite, evidencia, informe | RF-E, pruebas, riesgos de privacidad, informe |

### 7.4 Reglas de oro de los extras
- **No empezar** hasta que la etapa vigente esté en `main`, probada y etiquetada.
- **Una semana por extra** como máximo; si se atrasa, se corta.
- Todo extra nace **desactivado por bandera** en `config.py`; solo se activa para la demo si se ensayó.
- **Congelado** al final de la semana 14: después, solo correcciones.
- Si el extra amenaza con romper el circuito de Wokwi, **no se une a `main`**.
- Los extras **no reemplazan** ningún requisito de la guía: el informe los presenta como funcionalidades adicionales o trabajo futuro.

## 8. Requisitos de la guía que condicionan todo lo anterior

- Repositorio **privado** en GitHub con acceso para el docente.
- Firmware en **Wokwi (MicroPython)**; backend en **Python 3** con `requirements.txt`; conexión a una **plataforma en la nube** para la demostración.
- El circuito debe simular **sin errores** en Wokwi y el backend debe correr sin errores.
- Código organizado "de manera que pueda revisarse directamente" y, según la rúbrica, **limpio, comentado y sin duplicación**.
- Todos los integrantes deben poder **explicar todo el código** (política de IA de la guía).
- Informe en **Arial 12, justificado, márgenes de 2.54 cm**; formato PDF en la entrega final; referencias en formato IEEE.
