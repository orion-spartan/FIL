# Especificación del MVP de FIL

## Propósito

Este documento define el alcance funcional del primer MVP de `FIL`.

La meta es construir una herramienta local para Linux, operada por consola, capaz de:

1. crear y gestionar sesiones
2. capturar audio para dictado y reuniones
3. transcribir localmente
4. delegar tareas a OpenCode
5. mantener una base escalable para versiones futuras

## Objetivo del MVP

El MVP debe demostrar que `FIL` puede funcionar como plataforma del dominio de reuniones y dictado, mientras `OpenCode` actúa como orquestador sobre ese dominio.

El MVP no busca resolver todos los problemas desde la primera versión. Busca validar el flujo esencial end-to-end.

## Resultado esperado

Al terminar el MVP, un usuario debe poder:

1. iniciar una sesión
2. dictar una nota o grabar una reunión
3. obtener una transcripción local
4. ejecutar una instrucción sobre esa transcripción usando OpenCode
5. consultar sesiones previas y su estado

## Alcance funcional

Funciones incluidas en el MVP:

1. `CLI por subcomandos`
2. creación y persistencia de sesiones
3. captura inicial de audio
4. transcripción local con `faster-whisper`
5. integración con `opencode run`
6. tools internas del dominio expuestas de forma controlada
7. almacenamiento local de transcripciones y resultados

## Fuera de alcance

Funciones excluidas del MVP:

1. ventana flotante u overlay
2. hotkeys globales
3. shell interactivo completo
4. daemon persistente avanzado
5. multiusuario
6. sincronización en nube
7. shell abierta para OpenCode
8. acceso irrestricto a comandos del sistema

## Experiencia de uso

La interfaz oficial del MVP será por subcomandos.

Comandos previstos:

```bash
fil listen start
fil listen stop
fil listen live
fil dictate
fil do "resume la última reunión"
fil status
fil sessions list
fil sessions show <session-id>
```

Los slash commands pueden agregarse después como alias o modo interactivo, pero no forman parte del MVP inicial.

## Casos de uso principales

## 1. Dictado rápido

Flujo:

1. el usuario ejecuta `fil dictate`
2. FIL crea una sesión de tipo `dictation`
3. FIL captura audio del micrófono durante un intervalo corto o hasta que se detenga
4. FIL transcribe localmente
5. FIL guarda el resultado
6. el usuario puede ejecutar `fil do "convierte esto en tareas"`

## 2. Escucha de reunión

Flujo:

1. el usuario ejecuta `fil listen start`
2. FIL crea una sesión de tipo `meeting`
3. FIL comienza a capturar audio configurado
4. FIL genera transcripción por bloques
5. el usuario ejecuta `fil listen stop`
6. FIL cierra la sesión y guarda resultados

## 3. Acción de agente sobre sesión

Flujo:

1. el usuario ejecuta `fil do "resume esta reunión"`
2. FIL localiza la sesión activa o la última sesión relevante
3. FIL construye contexto con transcript y metadatos
4. FIL invoca `opencode run`
5. OpenCode produce el resultado
6. FIL guarda prompt, salida y metadatos asociados

## 4. Consulta de sesiones

Flujo:

1. el usuario ejecuta `fil sessions list`
2. FIL lista sesiones recientes
3. el usuario ejecuta `fil sessions show <session-id>`
4. FIL muestra el detalle de la sesión

## Modelo de sesiones

Tipos de sesión del MVP:

1. `meeting`
2. `dictation`
3. `agent-task`

Estados de sesión del MVP:

1. `created`
2. `running`
3. `stopped`
4. `completed`
5. `failed`

Campos mínimos por sesión:

1. `id`
2. `type`
3. `status`
4. `created_at`
5. `updated_at`
6. `title` opcional
7. `audio_path` opcional
8. `transcript_path` opcional
9. `metadata` serializable

## Comandos del MVP

## `fil listen start`

Responsabilidad:

1. crear una nueva sesión `meeting`
2. iniciar captura de audio
3. marcar la sesión como `running`

Resultado esperado:

1. imprime el `session-id`
2. informa la fuente de audio usada

## `fil listen stop`

Responsabilidad:

1. detener la sesión activa de escucha
2. cerrar recursos de audio
3. finalizar la transcripción pendiente
4. actualizar el estado de la sesión

Resultado esperado:

1. muestra el `session-id`
2. confirma estado final

## `fil listen live`

Responsabilidad:

1. iniciar una sesión de reunión en vivo
2. capturar audio del micrófono y/o del sistema
3. transcribir en tiempo casi real por bloques cortos
4. generar insights periódicos con OpenCode
5. mostrar transcript e insights en consola

Resultado esperado:

1. transcript incremental visible
2. resumenes/observaciones periódicas visibles
3. sesión persistida con metadatos e historia

## `fil dictate`

Responsabilidad:

1. crear una sesión `dictation`
2. capturar audio del micrófono
3. transcribir localmente
4. guardar el texto

Resultado esperado:

1. muestra el texto transcrito
2. registra la sesión

## `fil do "<instrucción>"`

Responsabilidad:

1. localizar el contexto de sesión aplicable
2. construir el prompt o payload para OpenCode
3. invocar `opencode run`
4. guardar el resultado como `agent-task` o asociado a la sesión fuente

Resultado esperado:

1. imprime la respuesta de OpenCode
2. guarda prompt, salida y relación con la sesión

## `fil status`

Responsabilidad:

1. mostrar si existe una sesión activa
2. mostrar tipo, estado y tiempos básicos

## `fil sessions list`

Responsabilidad:

1. listar sesiones recientes
2. mostrar id, tipo, estado y fecha

## `fil sessions show <session-id>`

Responsabilidad:

1. mostrar detalle de una sesión concreta
2. incluir transcripción o referencia a ella
3. incluir resultados de agente relacionados

## Integración con OpenCode

La integración oficial del MVP será mediante:

```bash
opencode run [message..]
```

Reglas del MVP:

1. FIL llama OpenCode como subprocess
2. FIL prepara el contexto antes de invocar OpenCode
3. OpenCode actúa como orquestador, no como dueño del dominio
4. FIL conserva la persistencia principal

Contexto mínimo enviado a OpenCode:

1. `session_id`
2. `session_type`
3. `session_status`
4. `transcript` o referencia seleccionada
5. `user_instruction`
6. `allowed_tools`

## Tools del dominio expuestas en el MVP

OpenCode no recibirá shell abierta en esta fase.

Tools candidatas del dominio para el MVP:

1. `fil_session_current`
   Devuelve la sesión activa o la más reciente relevante.

2. `fil_session_transcript`
   Devuelve transcript o fragmentos de transcript de una sesión.

3. `fil_session_summary`
   Devuelve un resumen almacenado si existe.

4. `fil_listen_start`
   Inicia una sesión de escucha.

5. `fil_listen_stop`
   Detiene una sesión de escucha.

No todas estas tools tienen que estar implementadas en el primer commit del MVP, pero sí forman parte del borde previsto.

## Políticas de ejecución

Políticas mínimas del MVP:

1. allowlist explícita de tools
2. timeout para ejecución de tools y subprocess
3. rutas restringidas al storage de FIL
4. logging por sesión
5. captura de stdout, stderr y exit code
6. sin shell arbitraria para OpenCode

## Persistencia

Persistencia inicial:

1. `SQLite` para metadatos
2. `filesystem local` para audio y transcripciones

Datos mínimos a guardar:

1. sesiones
2. transcript chunks o transcript final
3. archivos de audio asociados
4. prompts enviados a OpenCode
5. respuestas generadas
6. logs de ejecución de tools

## Requisitos no funcionales

El MVP debe cumplir estas características:

1. `Linux-first`
2. `local-first`
3. `modular`
4. `seguro por defecto`
5. `trazable`
6. `extensible`

## Orden recomendado de implementación

Secuencia sugerida:

1. estructura base del proyecto en Python
2. modelo de sesiones y almacenamiento
3. `fil do`
4. `fil sessions list` y `fil sessions show`
5. `fil dictate`
6. `fil listen start` y `fil listen stop`
7. tool registry y execution policy

## Criterios de aceptación

El MVP se considera válido si cumple lo siguiente:

1. existe una CLI funcional con los comandos principales documentados
2. FIL puede crear y consultar sesiones
3. FIL puede transcribir localmente al menos una sesión de dictado
4. FIL puede invocar `opencode run` con contexto asociado a una sesión
5. FIL guarda resultados de transcripción y de agente
6. FIL no expone shell abierta a OpenCode

## Riesgos del MVP

1. la captura de audio en Linux puede variar por entorno y configuración
2. la latencia de transcripción puede depender del hardware disponible
3. el empaquetado futuro como ejecutable único puede requerir ajustes especiales
4. la interfaz exacta de OpenCode puede requerir adaptación adicional al integrar tools

## Decisiones ya tomadas

1. lenguaje principal: `Python`
2. interfaz inicial: `CLI por subcomandos`
3. motor de transcripción: `faster-whisper`
4. orquestación: `OpenCode`
5. integración inicial con OpenCode: `opencode run`
6. persistencia: `SQLite + filesystem`
7. OpenCode solo usará tools del dominio en el MVP

## Decisiones pendientes

1. librería exacta de captura de audio
2. duración o estrategia de chunks de transcripción
3. formato exacto del transcript persistido
4. esquema inicial de base de datos
5. contrato exacto del registro de tools
