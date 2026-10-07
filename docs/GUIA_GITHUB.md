# Guía de trabajo con Git y GitHub – SLS

Manual del equipo para trabajar juntos en este repositorio sin pisarnos el trabajo. Está pensado para que cualquier integrante lo pueda seguir aunque sea su primera vez trabajando en equipo con Git.

> **Resumen en 10 reglas** (si solo vas a leer algo, lee esto)
> 1. `main` siempre debe funcionar. **Nadie sube directo a `main`.**
> 2. Cada tarea va en su **propia rama**, con nombre `tipo/area-descripcion`.
> 3. Los commits siguen el formato `tipo(alcance): descripción` en español, en presente.
> 4. Commits **pequeños y frecuentes**; un commit, una idea.
> 5. Todo llega a `main` mediante un **Pull Request (PR)** revisado por **otra persona**.
> 6. Si el cambio toca el firmware, **se prueba en Wokwi** antes de pedir revisión.
> 7. **Nunca** se suben contraseñas, claves ni archivos generados (`estado.json`, `historial.csv`).
> 8. Quien abre un PR **debe poder explicar cada línea**; quien lo revisa también.
> 9. El repositorio manda; **Wokwi es una copia** que se sincroniza.
> 10. Ante la duda o un lío con Git: **para y pregunta antes de forzar nada** (`--force`, `reset --hard`).

---

## Índice
1. [Principios](#1-principios)
2. [Configuración inicial](#2-configuración-inicial-una-sola-vez)
3. [Ramas](#3-ramas)
4. [Commits](#4-commits)
5. [Pull Requests](#5-pull-requests)
6. [Issues, etiquetas y milestones](#6-issues-etiquetas-y-milestones)
7. [Flujo diario paso a paso](#7-flujo-diario-paso-a-paso)
8. [Conflictos](#8-conflictos)
9. [Qué NO se sube y qué hacer si se filtra un secreto](#9-qué-no-se-sube-y-qué-hacer-si-se-filtra-un-secreto)
10. [Entregas, etiquetas y versiones](#10-entregas-etiquetas-y-versiones)
11. [Wokwi y el repositorio](#11-wokwi-y-el-repositorio)
12. [Funcionalidades extra](#12-funcionalidades-extra-puerta-y-cámara)
13. [Reglas de equipo](#13-reglas-de-equipo)
14. [Problemas comunes](#14-problemas-comunes)
15. [Chuleta de comandos](#15-chuleta-de-comandos)

---

## 1. Principios

- **Un solo código fuente.** Wokwi y la placa real usan el mismo código; solo cambian la configuración y los adaptadores de hardware.
- **Cambios pequeños.** Un PR pequeño se revisa en minutos y rara vez genera conflictos.
- **Cada carpeta tiene dueño** (ver tabla). El dueño decide, pero cualquiera puede proponer cambios mediante un PR.
- **Todos entienden todo.** La guía del curso establece que cualquier integrante puede ser preguntado sobre cualquier parte del código. La revisión cruzada es la forma de lograrlo.
- **Historia legible.** Los mensajes de commit y los títulos de PR cuentan la historia del proyecto; el profesor puede revisarla.

| Carpeta | Dueño principal | Revisa por defecto |
|---|---|---|
| `firmware/`, `wokwi/` | Líder / Firmware | Un desarrollador web |
| `backend/`, `dashboard/` | Desarrolladores web | Líder / Firmware |
| `tests/`, `docs/` | QA y Documentación | Cualquier otro integrante |
| `tools/`, raíz del repo | Quien lo cambie | Líder |

## 2. Configuración inicial (una sola vez)

### 2.1 Instalar y configurar Git
```bash
git --version                                   # comprobar que está instalado
git config --global user.name  "Nombre Apellido"
git config --global user.email "tu-correo@ejemplo.com"   # el mismo de tu cuenta de GitHub
git config --global init.defaultBranch main
git config --global pull.rebase false           # al hacer pull, se hace merge (más simple al empezar)
```

### 2.2 Crear el repositorio (lo hace una sola persona: el líder)
1. En GitHub: **New repository** → nombre sugerido `sls-smart-lighting` → **Private** (la guía exige repositorio privado).
2. **Settings → Collaborators** → agregar a los demás integrantes (permiso *Write*) y **al profesor José Collado** (permiso *Read* es suficiente). La guía exige que el docente tenga acceso.
3. Subir el contenido inicial (ver sección 10.1).

### 2.3 Clonar (todos los demás)
```bash
git clone https://github.com/<usuario-o-org>/sls-smart-lighting.git
cd sls-smart-lighting
```
Si GitHub pide contraseña por HTTPS, usa un *Personal Access Token* o configura una llave SSH.

### 2.4 Proteger `main` (lo hace el líder)
**Settings → Branches → Add branch protection rule** (o **Rulesets**), patrón `main`:
- ✅ Require a pull request before merging
- ✅ Require approvals → **1**
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require conversation resolution before merging
- ✅ Block force pushes (no permitir `push --force`)

> **Nota:** según el plan de la cuenta, GitHub puede no permitir reglas de protección en repositorios privados. Los estudiantes con el paquete *GitHub Student Developer Pack* suelen tener plan Pro. Si la opción no está disponible, **la regla se cumple por acuerdo del equipo**: nadie hace push a `main`.

## 3. Ramas

### 3.1 Modelo
Usamos **GitHub Flow**: una rama estable (`main`) y ramas cortas para cada tarea. No usamos `develop` (agrega complejidad que un equipo de cuatro no necesita). Las entregas de cada etapa se marcan con **etiquetas**, no con ramas (ver sección 10).

### 3.2 Nomenclatura
```
<tipo>/<area>-<descripcion-corta>
```
Todo en minúsculas, palabras separadas por guiones, sin tildes ni espacios.

| Tipo | Cuándo se usa |
|---|---|
| `feat` | Funcionalidad nueva |
| `fix` | Corrección de un error |
| `refactor` | Reorganizar código sin cambiar su comportamiento |
| `test` | Agregar o mejorar pruebas |
| `docs` | Documentación e informes |
| `chore` | Mantenimiento: estructura, `.gitignore`, configuración |

| Área | Corresponde a |
|---|---|
| `firmware`, `backend`, `dashboard`, `tools`, `tests`, `wokwi`, `docs`, `repo` | La carpeta o el aspecto que se toca |

**Ejemplos buenos**
```
feat/firmware-red-mqtt
feat/backend-receptor-json
fix/firmware-histeresis-ldr
refactor/firmware-modulos
test/tests-escenarios-limite
docs/docs-informe-etapa3
chore/repo-estructura-inicial
feat/dashboard-panel-zonas
```
**Ejemplos malos:** `arreglos`, `jorge`, `prueba2`, `nueva-rama`, `FixFinal`.

### 3.3 Reglas
- **Una rama = un objetivo.** Si descubres otra cosa que arreglar, crea otra rama.
- **Vida corta:** idealmente de 1 a 3 días. Una rama de dos semanas es una receta para conflictos.
- Siempre se crea **desde un `main` actualizado**.
- Se **borra** después de unirla.
- No se trabaja dos personas en la misma rama sin avisar.

## 4. Commits

### 4.1 Formato
Usamos **Conventional Commits en español**:

```
<tipo>(<alcance>): <descripción corta>

[cuerpo opcional: por qué se hizo, no qué se hizo]

[pie opcional: Closes #12 / Refs #8]
```

**Tipos** (los mismos que las ramas, más algunos):

| Tipo | Uso | Ejemplo |
|---|---|---|
| `feat` | Funcionalidad nueva | `feat(firmware): agrega interrupción del PIR en GPIO13` |
| `fix` | Corrección de error | `fix(firmware): corrige umbral de histéresis del LDR` |
| `refactor` | Reorganización sin cambio de comportamiento | `refactor(firmware): separa el control del 74HC595 en actuador_leds.py` |
| `test` | Pruebas | `test(firmware): agrega escenario sin eco en HC-SR04` |
| `docs` | Documentación | `docs(informe): agrega diagrama de arquitectura por capas` |
| `chore` | Mantenimiento | `chore(repo): ignora secrets.py en .gitignore` |
| `style` | Formato sin cambio de lógica (espacios, comentarios) | `style(backend): ordena importaciones` |
| `perf` | Mejora de rendimiento | `perf(firmware): reduce lecturas del LDR de 8 a 4` |
| `revert` | Revertir un commit | `revert: revierte "feat(backend): agrega validación"` |

**Alcances:** `firmware`, `backend`, `dashboard`, `tools`, `tests`, `wokwi`, `docs`, `informe`, `repo`.

### 4.2 Reglas del mensaje
- **Primera línea ≤ 72 caracteres**, sin punto final.
- **Verbo en presente** ("agrega", "corrige", "separa"), no "agregué" ni "agregando".
- Empieza en minúscula después de los dos puntos.
- Describe **el resultado**, no el esfuerzo: "corrige umbral del LDR", no "arreglo cosas".
- El cuerpo (opcional) explica el **por qué** cuando no es obvio.
- Cambio que rompe compatibilidad (por ejemplo, cambia el formato del JSON): agrega `!` → `feat(firmware)!: cambia el formato del mensaje a JSON` y explícalo en el cuerpo.
- Referencia issues en el pie: `Closes #12` (lo cierra al unir) o `Refs #12`.

### 4.3 Ejemplo completo
```
fix(firmware): evita parpadeo del LED azul con el LDR

El umbral único de 2000 hacía que el LED cambiara con cada lectura
cercana. Se usa histéresis: pasa a oscuro sobre 2150 y vuelve a claro
bajo 1850.

Closes #7
```

### 4.4 Commits malos
`arreglos` · `cambios` · `asdf` · `final` · `final2` · `ahora sí` · `wip` · `Update main.py`

### 4.5 Buenas prácticas
- **Un commit, una idea.** Si el mensaje necesita la palabra "y", probablemente son dos commits.
- Commitea **seguido**; no acumules un día de trabajo en un solo commit.
- Antes de commitear mira qué incluyes: `git status` y `git diff`.
- Agrega archivos **por nombre** (`git add firmware/main.py`) en lugar de `git add .`, para no subir algo por accidente.
- Corregir el **último** mensaje, **antes** de hacer push: `git commit --amend -m "nuevo mensaje"`.

## 5. Pull Requests

### 5.1 Cuándo
Siempre que se quiera llevar algo a `main`. Puedes abrir un **PR en borrador** (*Draft*) temprano para pedir opinión; se marca *Ready for review* cuando esté listo.

### 5.2 Título
Igual que un commit: `tipo(alcance): descripción`. Ejemplo: `feat(backend): recibe y valida mensajes MQTT en JSON`.

### 5.3 Descripción
GitHub carga automáticamente la plantilla de `.github/pull_request_template.md`. Complétala **entera**: qué cambia, por qué (RF/issue), cómo probarlo, evidencia y checklist.

### 5.4 Tamaño
- Objetivo: **menos de 400 líneas** cambiadas y **una sola cosa** por PR.
- Un PR enorme se revisa mal. Si crece, divídelo (por ejemplo: un PR de firmware, otro de backend, otro de dashboard).

### 5.5 Antes de pedir revisión (checklist del autor)
- [ ] Mi rama está **actualizada con `main`** (sección 7).
- [ ] Probé en Wokwi si toqué el firmware; corrí los tests si toqué el backend.
- [ ] No hay secretos ni archivos generados.
- [ ] Releí mi propio diff en la pestaña *Files changed*.
- [ ] Puedo **explicar cada línea**.

### 5.6 Revisión
- **Mínimo 1 aprobación** de alguien distinto al autor. Rotamos revisores para que todos conozcan todas las partes.
- **Plazo:** responder en máximo **24 horas**. Si no puedes, avisa.
- **Qué se mira:** ¿hace lo que dice?, ¿se entiende?, ¿se probó?, ¿rompe algo?, ¿hay secretos?, ¿sigue la estructura y la nomenclatura?, ¿hay código duplicado?
- **Cómo se comenta** (prefijos para que el tono no se malinterprete):
  - `bloqueante:` hay que arreglarlo antes de unir.
  - `pregunta:` no entiendo esto, explícame.
  - `sugerencia:` puede mejorar, pero no bloquea.
  - `nit:` detalle menor.
- Si **no entiendes algo, pregunta**. Aprobar sin entender va contra la regla 8.
- Se critica el código, no a la persona.
- El autor resuelve cada conversación (corrige o explica) y el revisor la marca como resuelta.

### 5.7 Unir (merge)
- Método: **Squash and merge**. Deja un solo commit limpio por PR, y el título del PR pasa a ser el mensaje del commit en `main`.
- Une **el autor**, después de la aprobación y con las conversaciones resueltas.
- Al unir: **Delete branch**.
- Si el PR cierra un issue, debe incluir `Closes #n` en la descripción.

## 6. Issues, etiquetas y milestones

Cada tarea no trivial tiene un **issue** (pestaña *Issues*). Un issue contiene: qué hay que hacer, criterio de terminado, responsable y milestone.

**Plantilla mínima de issue**
```
## Qué hay que hacer
...
## Criterio de terminado
- [ ] ...
- [ ] ...
## Requerimiento relacionado
RF-03
```

**Etiquetas (labels)** sugeridas: `firmware`, `backend`, `dashboard`, `tests`, `docs`, `wokwi`, `bug`, `mejora`, `extra`, `bloqueado`, `urgente`.

**Milestones** = hitos de la guía del curso:
- `Etapa 3 – Comunicación (semana 12)`
- `Etapa 4 – Entrega final (semana 16)`
- `Extras`

Se puede usar la pestaña **Projects** de GitHub como tablero (columnas *Por hacer / En curso / En revisión / Hecho*).

**Vínculo con requerimientos:** numeramos los requerimientos del informe (RF-01, RF-02, RNF-01…) y los citamos en issues, PRs y pruebas. Así la tabla de verificación final del informe sale casi sola.

## 7. Flujo diario paso a paso

```bash
# 1) Empezar desde main actualizado
git switch main
git pull origin main

# 2) Crear tu rama
git switch -c feat/firmware-red-mqtt

# 3) Trabajar y revisar qué cambió
git status
git diff

# 4) Guardar cambios (commits pequeños)
git add firmware/red.py firmware/config.py
git commit -m "feat(firmware): agrega conexión WiFi a Wokwi-GUEST"

# 5) Subir la rama (la primera vez con -u)
git push -u origin feat/firmware-red-mqtt

# 6) En GitHub: abrir el Pull Request y pedir revisión
```

**Mantener tu rama al día** (hazlo antes de abrir el PR y cuando `main` cambie):
```bash
git fetch origin
git merge origin/main
```

**Después de que unieron tu PR:**
```bash
git switch main
git pull origin main
git branch -d feat/firmware-red-mqtt     # borra la rama local
git fetch --prune                         # limpia referencias a ramas borradas
```

## 8. Conflictos

Un conflicto aparece cuando dos personas cambian las mismas líneas. **No es un error grave.**

**Cómo evitarlos**
- PRs pequeños y ramas cortas.
- Respetar los dueños de carpeta; avisar en el chat antes de tocar archivos ajenos.
- No reformatear archivos enteros "de paso".
- Traer `main` con frecuencia.

**Cómo resolverlos**
1. `git fetch origin` y `git merge origin/main` → Git avisa de los archivos en conflicto.
2. Abre cada archivo y busca las marcas:
   ```
   <<<<<<< HEAD
   tu versión
   =======
   la versión de main
   >>>>>>> origin/main
   ```
3. Decide qué queda (a veces las dos), **borra las marcas** y guarda.
4. `git add <archivo>` y luego `git commit` (acepta el mensaje de merge).
5. **Vuelve a probar** (Wokwi/tests) antes de subir.
6. ¿Te perdiste? `git merge --abort` te devuelve al estado anterior.

Si el conflicto es en código de otra persona, **hablen**: resolverlo entre los dos es más seguro que adivinar.

## 9. Qué NO se sube y qué hacer si se filtra un secreto

**No se sube nunca:**
- Contraseñas WiFi, claves de API, tokens, credenciales del broker o de la nube → `firmware/secrets.py`, archivos `.env`.
- Archivos generados: `estado.json`, `historial.csv`, `backend/datos/*`, `__pycache__/`.
- Entornos virtuales (`.venv/`).

El `.gitignore` ya cubre esto. Lo que sí se sube es la **plantilla** `firmware/secrets_example.py` con valores falsos, para que los demás sepan qué campos llenar.

**Si subiste un secreto por accidente:**
1. **Cambia la credencial de inmediato** (contraseña, token, clave). Borrar el archivo en un commit nuevo **no basta**: el secreto queda en el historial.
2. Avisa al equipo.
3. Si hace falta limpiar el historial, se hace entre todos y con cuidado (por ejemplo con `git filter-repo`); pregunta antes de intentarlo solo.

## 10. Entregas, etiquetas y versiones

### 10.1 Primer día: subir el contenido inicial (líder)
```bash
git init -b main
git add .
git commit -m "chore(repo): importa la entrega de la Etapa 2 y la estructura inicial"
git remote add origin https://github.com/<usuario-o-org>/sls-smart-lighting.git
git push -u origin main
git tag -a etapa-2 -m "Entrega Etapa 2 (semana 8)"
git push origin etapa-2
```
Así queda congelada, con la etiqueta `etapa-2`, la versión exacta que se entregó.

### 10.2 Etiquetas por etapa
| Etiqueta | Entrega |
|---|---|
| `etapa-2` | Procesamiento de datos y módulo embebido (semana 8) |
| `etapa-3` | Módulo de comunicación (semana 12) |
| `etapa-4` | Entrega final (semana 16) |

### 10.3 Procedimiento antes de cada entrega
1. **Congelar:** una semana antes de la entrega solo entran correcciones de errores, no funcionalidades nuevas.
2. Verificar que `main` pasa la lista: Wokwi corre sin errores, el backend corre con `requirements.txt`, el README explica cómo ejecutarlo, no hay secretos.
3. Crear la etiqueta:
   ```bash
   git switch main && git pull origin main
   git tag -a etapa-3 -m "Entrega Etapa 3 (semana 12)"
   git push origin etapa-3
   ```
4. En GitHub: **Releases → Draft a new release** sobre esa etiqueta, con notas de lo que incluye.
5. Confirmar que el profesor sigue teniendo acceso.

## 11. Wokwi y el repositorio

- **El repositorio manda; Wokwi es una copia.** Wokwi web no guarda historial de equipo ni tiene carpetas.
- Cuando `firmware/` cambia en `main`, el **guardián de Wokwi** de la semana (se rota) pega los archivos en el proyecto de Wokwi y anota en `wokwi/README.md` el commit con el que quedó sincronizado.
- **Nadie edita directamente en Wokwi** sin pasar por el repo. Si algo se arregla "rápido en Wokwi", ese arreglo se copia al repo en el mismo día mediante un PR.
- El `diagram.json` del circuito se guarda en `wokwi/diagram.json`, de modo que los cambios de hardware también quedan versionados.
- Un PR de firmware debe incluir **evidencia de Wokwi** (captura o salida de consola).

## 12. Funcionalidades extra (puerta y cámara)

Las funcionalidades extra son **secundarias**: primero se cumple todo lo que pide el profesor en cada etapa.

- **Compuerta de entrada:** no se empieza un extra hasta que la etapa vigente esté en `main`, probada y etiquetada.
- Cada extra tiene su **milestone `Extras`**, su etiqueta `extra` y su rama `feat/extra-...`.
- Se divide en **PRs por capa** (firmware, backend, dashboard, tests), igual que cualquier otra funcionalidad.
- Todo extra nace **desactivado** mediante una bandera en `config.py` (por ejemplo `HABILITAR_PUERTA = False`), de modo que el circuito base de Wokwi no puede romperse por un extra a medio terminar.
- **Congelado de extras:** al final de la semana 14 solo se aceptan correcciones.

## 13. Reglas de equipo

- **Reunión semanal** de 15 a 20 minutos: qué se hizo, qué sigue, qué bloquea. Se anotan acuerdos en `docs/bitacora.md`.
- **Recorrido cruzado:** cada semana, un integrante explica al resto un módulo que **no escribió**. Es el mejor ensayo para la presentación oral.
- **Uso de IA:** está permitido como apoyo, pero el equipo es responsable de entender, explicar y defender cada línea. Si una parte del código no se puede explicar, esa sección no recibe crédito. En los PRs que usaron asistencia de IA, el autor lo dice en las notas y confirma que entiende el código.
- **Código de referencia:** si se adapta código de otra fuente, se cita en el informe (el límite de la guía es menos del 20 % del código total).
- **Comunicación:** si vas a tocar un archivo que no es tuyo, avisa antes.
- **Plazos:** una entrega tardía pierde 10 puntos por día; planifiquen con margen.

## 14. Problemas comunes

**Hice commits en `main` por error y todavía no hice push**
```bash
git branch feat/mi-trabajo          # guarda lo que hiciste en una rama nueva
git reset --hard origin/main        # deja main como el remoto  (¡solo si NO hiciste push!)
git switch feat/mi-trabajo
```

**Hice push a `main` con algo roto**
No uses `reset` ni `--force`. Avisa y revierte con un commit nuevo:
```bash
git revert <hash-del-commit>
git push origin main
```

**Me equivoqué en el mensaje del último commit (sin push)**
```bash
git commit --amend -m "mensaje correcto"
```

**Me faltó un archivo en el último commit (sin push)**
```bash
git add archivo-olvidado.py
git commit --amend --no-edit
```

**Quiero deshacer el último commit pero conservar los cambios**
```bash
git reset --soft HEAD~1
```

**Mi rama quedó atrás de `main`**
```bash
git fetch origin
git merge origin/main
```

**Git dice que hay cambios sin guardar y no me deja cambiar de rama**
```bash
git stash            # guarda los cambios en un cajón temporal
git switch otra-rama
git stash pop        # los recupera
```

**Subí un archivo que no debía** (que no es un secreto)
```bash
git rm --cached ruta/del/archivo
git commit -m "chore(repo): deja de versionar archivo generado"
```
y agrégalo al `.gitignore`. Si era un secreto, ver sección 9.

**`git push` me rechaza**
Casi siempre es porque alguien subió a esa rama antes. Haz `git pull` (o `git fetch` + `git merge`), resuelve y vuelve a intentar. **No uses `--force`.** Solo en tu propia rama personal, y con `--force-with-lease`, y avisando al equipo.

## 15. Chuleta de comandos

| Quiero… | Comando |
|---|---|
| Ver en qué estado estoy | `git status` |
| Ver qué cambié | `git diff` |
| Ver el historial resumido | `git log --oneline --graph --decorate -15` |
| Crear una rama y cambiarme | `git switch -c tipo/area-descripcion` |
| Cambiar de rama | `git switch nombre-rama` |
| Guardar archivos para el commit | `git add ruta/archivo` |
| Hacer commit | `git commit -m "tipo(alcance): descripción"` |
| Subir mi rama | `git push -u origin nombre-rama` |
| Traer cambios del remoto | `git pull origin main` |
| Traer `main` a mi rama | `git fetch origin` y `git merge origin/main` |
| Borrar rama local | `git branch -d nombre-rama` |
| Ver ramas | `git branch -a` |
| Crear etiqueta de entrega | `git tag -a etapa-3 -m "Entrega Etapa 3"` y `git push origin etapa-3` |
| Cancelar un merge con conflictos | `git merge --abort` |

**Peligrosos: pensar dos veces antes de usarlos**
`git push --force` · `git reset --hard` · `git clean -fd` · `git rebase` sobre ramas compartidas.
