# SLS – Smart Lighting System (Casa Inteligente IoT)

Sistema IoT de iluminación inteligente para el hogar. Un **ESP32** programado en **MicroPython** lee tres sensores (presencia con PIR, distancia con HC-SR04 y luz ambiental con LDR), controla las luces (LEDs mediante un registro de desplazamiento 74HC595) y enviará sus datos a un **backend en Python 3** para procesarlos, guardarlos y mostrarlos en un panel de monitoreo y control.

> Proyecto semestral · Desarrollo de Software VIII · Universidad Tecnológica de Panamá · Grupo 1GS133 · Prof. José Collado

---

## Estado de las etapas

| Etapa | Entrega | Puntos | Estado |
|---|---|---|---|
| 1 – Propuesta y planificación | Semana 4 | 10 | ✅ Entregada |
| 2 – Procesamiento de datos y módulo embebido | Semana 8 | 30 | ✅ Entregada (etiqueta `etapa-2`) |
| 3 – Módulo de comunicación (Wokwi → broker/servidor, JSON) | Semana 12 | 15 | ⏳ En preparación |
| 4 – Entrega final (informe, sistema integrado, presentación) | Semana 16 | 45 | ⏳ Pendiente |

## Arquitectura (por capas)

```
 Sensores y LEDs ──▶ ESP32 (firmware MicroPython) ──WiFi──▶ Broker MQTT ──▶ Backend Python ──▶ Dashboard
                          ▲                                                       │
                          └────────────── comandos desde el panel ◄───────────────┘
```

El detalle de las decisiones está en [`docs/PLAN_PROYECTO.md`](docs/PLAN_PROYECTO.md).

## Estructura del repositorio

```
sls-smart-lighting/
├── README.md
├── .gitignore
├── .github/pull_request_template.md   # plantilla automática de Pull Request
├── firmware/      # MicroPython. PLANO a propósito: se pega tal cual en Wokwi y se copia a la placa
├── backend/       # Python 3: recibe, valida, procesa y guarda (requirements.txt)
├── dashboard/     # Panel web de monitoreo y control
├── tools/         # Herramientas de apoyo (simulación de sensores de la Etapa 2)
├── tests/         # Pruebas
├── wokwi/         # diagram.json y enlace al proyecto de Wokwi
└── docs/          # Informes, guías, diagramas, requerimientos
```

## Cómo ejecutar lo que existe hoy

### 1. Firmware en Wokwi
1. Abre el proyecto: <https://wokwi.com/projects/476828453604708353>
2. Reemplaza el contenido de `main.py` por el de [`firmware/main.py`](firmware/main.py).
3. Inicia la simulación y mueve el PIR, cambia la distancia del HC-SR04 o la luz del LDR. Verás los mensajes en la consola, por ejemplo `Interrupcion de hardware del PIR (IRQ #1)`.

### 2. Simulación de sensores en Python (Etapa 2)
Requiere Python 3.8 o superior. Desde la raíz del repositorio:

```bash
python tools/simulacion_sensores.py --ciclos 40 --pausa 0 --semilla 7
```

Genera `estado.json` e `historial.csv` en la carpeta desde donde lo ejecutas (están ignorados por Git). Para repetir exactamente la misma corrida, borra esos dos archivos antes de ejecutar y usa `--semilla`.

### 3. Pruebas del firmware (ESP32 simulado en Python)
```bash
python tests/prueba_main.py
```

## Equipo y roles

| Integrante | Rol | Carpetas principales |
|---|---|---|
| Jorge | Líder de proyecto / Firmware | `firmware/`, `wokwi/` |
| Rubén | Desarrollador web | `backend/`, `dashboard/` |
| Abrahan | Desarrollador web | `backend/`, `dashboard/` |
| Francesco | QA, pruebas y documentación | `tests/`, `docs/` |

Todos revisan el código de todos: cualquier integrante puede ser interrogado sobre cualquier parte del proyecto.

## Cómo trabajamos

Antes de tocar nada, lee [`docs/GUIA_GITHUB.md`](docs/GUIA_GITHUB.md): ramas, commits, Pull Requests y reglas del equipo.

## Documentación

- [`docs/PLAN_PROYECTO.md`](docs/PLAN_PROYECTO.md): arquitectura, estructura, reparto de tareas y plan por semanas.
- [`docs/GUIA_GITHUB.md`](docs/GUIA_GITHUB.md): manual de trabajo con Git y GitHub.
- [`docs/Informe_Etapa2.docx`](docs/Informe_Etapa2.docx): informe entregado de la Etapa 2.
