# SLS · Mi hogar

Dashboard local en español: plano interactivo de las tres zonas, lecturas de
PIR/HC-SR04/LDR, historial con filtros, CSV e importación de eventos JSON v1.
HTML/CSS/JavaScript modular, sin compilación, CDN ni dependencias de npm.

## Abrir

Desde la raíz del repositorio, con Python 3.9 o superior:

```bash
python backend/servidor.py
```

Abre **http://127.0.0.1:8000**. Ctrl+C detiene el servidor. Si el puerto está
ocupado, usa `--port 8001`. No abras `index.html` con doble clic: requiere HTTP.

## Fuentes de datos

**Demostración:** modo inicial. Datos ficticios en memoria del navegador, cambios
cada 12 segundos y controles manuales simulados. Controlar manualmente una zona
pausa su automatización hasta pulsar «Volver a auto». «Apagar todas» actúa solo
en la demo. Recargar la reinicia. No se guarda en el backend ni genera MQTT.

**Conectado:** exclusivamente eventos recibidos/importados por el backend.
Sin eventos muestra «Sin datos». Consulta cada 2,5 segundos; si el servidor falla,
avisa que los datos pueden estar desactualizados. Un receptor MQTT conectado no
prueba que la placa esté conectada: también se muestra si hay eventos recientes.
Es el último estado conocido, no una medición continua. Las horas corresponden
a la recepción y se muestran en la zona horaria de Panamá.

Los interruptores reales están deshabilitados: el firmware aún no recibe comandos.
No se estima consumo/ahorro porque el circuito no mide energía eléctrica.

## Probar sin broker

1. Explora el plano y las tarjetas en modo demostración.
2. En Mis zonas, apaga una luz: cambian plano, contador e historial simulado.
3. En Actividad, combina filtro de zona y «apagada»; exporta CSV.
4. Pulsa «Ver datos reales»: inicialmente no habrá eventos.
5. Importa `dashboard/ejemplos/evento.json`. Es ficticio, identificado como
   `ejemplo-sin-placa`, y quedará guardado como importación.
6. Importa el mismo archivo otra vez: se omite el duplicado.

Para no mezclar pruebas con tu base habitual, usa otra instancia:

```bash
python backend/servidor.py --port 8001 --datos backend/datos/pruebas
```

Se importan hasta 1000 eventos por lote, máximo 500 KB. La interfaz muestra
los últimos 1000 eventos; la exportación del panel aplica los filtros actuales.

## MQTT y pruebas

Configuración en [backend/README.md](../backend/README.md). Backend y ESP32 deben
usar el mismo broker y tópico. No se contacta un broker externo por defecto.
Falta validar ESP32/Wokwi → broker real → backend → dashboard.

```bash
node --test tests/test_dashboard.mjs
python -m unittest discover -s tests -p test_backend_dashboard.py -v
```

`index.html`: estructura y plano. `styles.css`: diseño adaptable.
`model.mjs`: estado y utilidades sin DOM. `app.mjs`: interacción y API.

La plataforma en nube y el control remoto de la placa siguen pendientes.
