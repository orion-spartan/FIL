# Plan de Trabajo

## Objetivo

Este plan divide la construcción de `FIL` en fases pequeñas, ejecutables y escalables.

La idea es avanzar desde una base mínima de consola hasta una herramienta capaz de:

1. gestionar sesiones
2. capturar audio
3. transcribir localmente
4. delegar tareas a OpenCode
5. crecer sin rehacer el núcleo

## Principios del plan

1. construir primero el esqueleto del sistema
2. validar cada fase con algo usable
3. evitar meter audio y agentes al mismo tiempo
4. mantener a `FIL` como dueño del dominio
5. introducir OpenCode de forma controlada

## Fase 0: Base documental

Objetivo:

1. dejar claro qué es FIL y cómo va a crecer

Entregables:

1. `README.md`
2. `ARCHITECTURE.md`
3. `OPENCODE.md`
4. `SPEC.md`
5. `PLAN_DE_TRABAJO.md`

Estado esperado:

1. visión, arquitectura y alcance del MVP definidos

## Fase 1: Motor de consola

Objetivo:

1. crear la base de la CLI y su estructura de comandos

Entregables:

1. estructura inicial del proyecto en Python
2. comando raíz `fil`
3. subcomandos mínimos:
   `status`, `do`, `sessions list`, `sessions show`
4. salida básica en consola

Herramientas:

1. `Python`
2. `Typer`
3. `Rich`

Resultado esperado:

1. `fil --help` funciona
2. `fil status` funciona
3. `fil sessions list` funciona
4. `fil do "..."` existe, aunque al inicio use stub o integración mínima

## Fase 2: Modelo de sesiones y persistencia

Objetivo:

1. darle memoria real a FIL

Entregables:

1. modelo `Session`
2. estados y tipos de sesión
3. persistencia local con `SQLite`
4. acceso a archivos locales para transcript y audio

Herramientas:

1. `sqlite3`
2. `pathlib`
3. utilidades internas de storage

Resultado esperado:

1. FIL puede crear sesiones
2. FIL puede listar sesiones previas
3. FIL puede mostrar detalle de una sesión

## Fase 3: Integración inicial con OpenCode

Objetivo:

1. conectar FIL con OpenCode de forma simple y real

Entregables:

1. adaptador `OpenCodeRunner`
2. integración con `opencode run`
3. almacenamiento de prompts y respuestas
4. asociación entre tarea de agente y sesión

Herramientas:

1. `subprocess`
2. `opencode run`

Resultado esperado:

1. `fil do "..."` ejecuta una instrucción real
2. FIL guarda el resultado
3. FIL mantiene el contexto de sesión

## Fase 4: Dictado local

Objetivo:

1. permitir capturar voz y convertirla a texto localmente

Entregables:

1. comando `fil dictate`
2. captura de audio desde micrófono
3. transcripción local básica
4. guardado del resultado como sesión `dictation`

Herramientas:

1. `faster-whisper`
2. `ffmpeg`, `pw-record` o librería de captura seleccionada

Resultado esperado:

1. el usuario dicta una nota
2. FIL devuelve texto transcrito
3. la nota queda guardada en historial

## Fase 5: Escucha de reuniones

Objetivo:

1. grabar y transcribir sesiones de reunión

Entregables:

1. `fil listen start`
2. `fil listen stop`
3. captura por bloques o flujo continuo controlado
4. guardado de transcript y audio

Herramientas:

1. stack de audio Linux
2. `faster-whisper`

Resultado esperado:

1. FIL crea una sesión `meeting`
2. FIL transcribe audio de la reunión
3. el usuario puede consultar el resultado después

## Fase 6: Tools del dominio

Objetivo:

1. exponer herramientas internas para que OpenCode orqueste sobre ellas

Entregables:

1. `ToolRegistry`
2. `ToolExecutor`
3. `ExecutionPolicy`
4. primeras tools del dominio:
   `fil_session_current`, `fil_session_transcript`, `fil_session_summary`

Resultado esperado:

1. OpenCode usa tools controladas de FIL
2. FIL sigue siendo dueño del dominio
3. no existe shell abierta para OpenCode

## Fase 7: Pulido del MVP

Objetivo:

1. cerrar el MVP con estabilidad mínima y buena experiencia de consola

Entregables:

1. mejores mensajes de error
2. logging básico
3. configuración inicial
4. validación del flujo end-to-end
5. documentación de uso

Resultado esperado:

1. el MVP cumple los criterios definidos en `SPEC.md`

## Fase 8: Evolución posterior

Posibles pasos después del MVP:

1. daemon persistente
2. shell interactivo
3. alias tipo slash commands
4. integración con `opencode serve`
5. integración con `opencode acp`
6. overlay o ventana flotante
7. empaquetado como ejecutable único

## Orden recomendado inmediato

El siguiente orden de trabajo es el más recomendable:

1. Fase 1: motor de consola
2. Fase 2: sesiones y persistencia
3. Fase 3: `fil do` con OpenCode
4. Fase 4: `fil dictate`
5. Fase 5: `fil listen`
6. Fase 6: tooling layer
7. Fase 7: pulido del MVP

## Primera meta concreta

La primera meta de implementación debe ser esta:

1. crear la estructura Python del proyecto
2. levantar la CLI con `Typer`
3. hacer funcionar `fil --help`
4. agregar `fil status`
5. agregar `fil sessions list`
6. preparar `fil do`

## Criterio de avance

No pasar a la siguiente fase sin tener una salida mínima usable en la fase actual.

La idea es que cada fase deje algo verificable, aunque todavía sea pequeño.
