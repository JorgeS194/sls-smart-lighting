# backend/

Backend en **Python 3** (requisito de la guía del curso). Recibe los mensajes del ESP32, los valida, los procesa y los guarda.

## Responsabilidades (plan)
- `main.py`: arranque; se suscribe al broker.
- `receptor.py`: recibe y **valida** cada mensaje JSON (excepciones controladas ante datos rotos).
- `procesamiento.py`: eventos y estado actual de la casa.
- `persistencia.py`: `estado.json` (cómo está la casa ahora) e `historial.csv` (todo lo que pasó). Reutiliza lo hecho en `tools/simulacion_sensores.py`.
- `datos/`: archivos generados (ignorados por Git).

## Dependencias
Todas las dependencias se listan en `requirements.txt`. Cualquier miembro debe poder correr el backend con:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    |    Linux/Mac: source .venv/bin/activate
pip install -r backend/requirements.txt
```

Cada vez que se agregue una librería, se agrega a `requirements.txt` en el mismo Pull Request.
