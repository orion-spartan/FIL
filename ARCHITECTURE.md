# Arquitectura de FIL

## Propósito

Este documento define la arquitectura base de `FIL` como una herramienta local para Linux orientada a:

1. grabación de reuniones
2. transcripción local
3. dictado
4. ejecución de acciones por comandos
5. integración con OpenCode

La meta es construir un sistema simple en su primera versión, pero con una estructura que permita crecer sin reescribir el núcleo.

## Principios

Principios de diseño para `FIL`:

1. `local-first`
   El audio y la transcripción deben procesarse localmente siempre que sea posible.

2. `monolito modular`
   La primera versión será una sola aplicación, pero organizada por módulos claros.

3. `interfaces estables`
   Los servicios clave deben depender de contratos internos, no de implementaciones concretas.

4. `CLI-first`
   La primera interfaz será de consola. Otras interfaces pueden agregarse después sin reescribir la lógica.

5. `sesiones como unidad principal`
   Reuniones, dictados y comandos deben poder asociarse a sesiones identificables.

6. `integración real con OpenCode`
   FIL debe integrarse por CLI, server o ACP, no por automatización de teclado o foco de ventanas.

7. `FIL como plataforma de dominio`
   FIL es dueño del audio, sesiones, transcripciones, persistencia y tools del dominio.

8. `OpenCode como orquestador`
   OpenCode decide cómo encadenar acciones, pero no debe absorber la lógica base del sistema.

9. `ejecución controlada de tools`
   Las tools disponibles para OpenCode deben exponerse bajo políticas explícitas.

## Visión general

La arquitectura propuesta se divide en cinco capas:

1. `Interface Layer`
2. `Application Layer`
3. `Domain Layer`
4. `Tooling Layer`
5. `Infrastructure Layer`

```text
Usuario
  |
  v
CLI / Shell / UI futura
  |
  v
Casos de uso de aplicación
  |
  v
Dominio y modelo de sesiones
  |
  v
Registry de tools y políticas de ejecución
  |
  v
Audio / STT / OpenCode / SQLite / Filesystem
```

## Capas

## 1. Interface Layer

Es la capa que recibe interacción del usuario.

Interfaces previstas:

1. `CLI por subcomandos`
   Primera interfaz oficial.

2. `Shell interactivo`
   Posible evolución posterior.

3. `Overlay o ventana flotante`
   Posible evolución futura en Linux.

Responsabilidades:

1. parsear argumentos
2. validar entrada del usuario
3. invocar casos de uso
4. mostrar resultados y errores

La lógica de negocio no debe vivir aquí.

## 2. Application Layer

Coordina operaciones de alto nivel.

Ejemplos de casos de uso:

1. `StartListening`
2. `StopListening`
3. `DictateNote`
4. `RunAgentCommand`
5. `SummarizeSession`
6. `ListSessions`
7. `GetStatus`

Responsabilidades:

1. orquestar servicios
2. abrir o cerrar sesiones
3. decidir qué infraestructura llamar
4. manejar flujos de trabajo

Esta capa conoce el dominio, pero no debe depender de detalles concretos del sistema de audio o del motor de transcripción.

## 3. Domain Layer

Contiene las entidades y reglas internas del sistema.

Entidades iniciales sugeridas:

1. `Session`
   Representa una reunión, dictado o tarea.

2. `TranscriptChunk`
   Fragmento de transcripción asociado a una sesión.

3. `AudioSegment`
   Fragmento de audio almacenado o procesado.

4. `AgentTask`
   Instrucción enviada a OpenCode u otro agente.

5. `CommandResult`
   Resultado estructurado de una acción del sistema.

6. `SessionStatus`
   Estado de una sesión: activa, detenida, completada, fallida.

Responsabilidades:

1. modelar el estado del sistema
2. expresar reglas del negocio
3. ofrecer tipos coherentes a toda la aplicación

## 4. Infrastructure Layer

## 4. Tooling Layer

Es la capa que define qué herramientas puede usar el sistema y, en particular, qué herramientas puede orquestar OpenCode.

Componentes previstos:

1. `ToolRegistry`
   Lista de tools disponibles y sus metadatos.

2. `ToolExecutor`
   Ejecuta tools con validaciones, timeout y captura de salida.

3. `ExecutionPolicy`
   Define allowlists, límites y capacidades permitidas.

4. `ToolAdapters`
   Envuelven herramientas internas de FIL y comandos externos aprobados.

Responsabilidades:

1. separar tools internas de comandos arbitrarios del sistema
2. controlar argumentos y contexto
3. registrar invocaciones y resultados
4. proteger el sistema frente a ejecuciones no deseadas

FIL debe privilegiar tools propias del dominio por encima de acceso crudo a la shell.

## 5. Infrastructure Layer

Implementa acceso a sistemas concretos.

Submódulos previstos:

1. `Audio`
   Captura desde micrófono y salida del sistema.

2. `Transcription`
   Implementación con `faster-whisper`.

3. `Agents`
   Integración con `OpenCode` como orquestador.

4. `Storage`
   Persistencia en `SQLite` y archivos locales.

5. `Config`
   Carga de configuración, rutas y parámetros del sistema.

Responsabilidades:

1. traducir contratos internos a operaciones reales
2. encapsular dependencias externas
3. permitir reemplazo futuro de implementaciones

### Feedback En Vivo

Las capacidades de feedback en vivo, como medidores de audio, no deben depender del pipeline de transcripción.

Reglas:

1. el transcript y el metering deben poder correr de forma independiente
2. el metering debe exponer estado por fuente cuando existan múltiples entradas, por ejemplo `mic` y `system`
3. la UI de consola solo debe renderizar ese estado; no calcularlo
4. estos runtimes deben ser reutilizables por `talk`, `dictate`, `listen` y futuros comandos de diagnóstico

## Modelo de responsabilidades

La relación entre `FIL` y `OpenCode` queda definida así:

1. `FIL`
   Posee el dominio de reuniones, audio, sesiones, persistencia y tools internas.

2. `OpenCode`
   Interpreta instrucciones, planifica pasos y orquesta tools expuestas por FIL.

3. `Infraestructura externa`
   Incluye `faster-whisper`, Linux audio stack, filesystem y SQLite.

Regla base:

1. OpenCode no es dueño de la captura de audio.
2. OpenCode no escribe directamente la persistencia principal fuera de las rutas definidas por FIL.
3. OpenCode opera sobre contexto y tools que FIL le entrega.

## Flujo principal del MVP

Flujo esperado para una sesión de escucha:

1. el usuario ejecuta `fil listen start`
2. la CLI invoca el caso de uso `StartListening`
3. se crea una nueva `Session`
4. el servicio de audio comienza a capturar fragmentos
5. cada fragmento se envía al transcriptor
6. la transcripción se guarda como `TranscriptChunk`
7. la sesión se mantiene activa hasta `fil listen stop`
8. el usuario puede ejecutar `fil do "resume esta reunión"`
9. FIL construye un contexto estructurado a partir de la sesión
10. FIL entrega a OpenCode el objetivo y las tools permitidas
11. OpenCode decide qué pasos seguir
12. si necesita datos o acciones, usa tools registradas por FIL
13. FIL ejecuta esas tools bajo política de ejecución
14. FIL guarda el resultado final

## Flujo de dictado

1. el usuario ejecuta `fil dictate`
2. FIL crea una sesión de tipo `dictation`
3. captura audio del micrófono durante un intervalo corto
4. transcribe el audio localmente
5. guarda el texto como nota o resultado
6. opcionalmente delega una acción a OpenCode
7. OpenCode puede usar tools de FIL para enriquecer o transformar el resultado

## Integración con OpenCode

Estrategia por etapas:

1. `Etapa 1`
   Integración por subprocess usando `opencode run`.

2. `Etapa 2`
   Integración persistente usando `opencode serve`.

3. `Etapa 3`
   Orquestación avanzada usando `opencode acp`.

Contrato interno sugerido para agentes:

```text
AgentRunner.run(task, session_context, options) -> CommandResult
```

Esto permite cambiar la implementación sin tocar la CLI ni los casos de uso.

Contrato interno sugerido para tools:

```text
Tool.execute(input, session_context, policy) -> CommandResult
```

OpenCode debe consumir tools a través de este borde y no a través de acceso irrestricto al shell.

## Tooling y políticas de ejecución

Clasificación inicial de tools:

1. `Domain tools`
   Tools propias de FIL como iniciar escucha, detener escucha, obtener transcript o resumir una sesión.

2. `System tools approved`
   Herramientas externas permitidas como `ffmpeg`, `pw-record` o similares cuando FIL las necesite.

3. `Blocked tools`
   Cualquier comando no aprobado por política.

Políticas mínimas del MVP:

1. allowlist explícita de tools
2. timeout por ejecución
3. rutas válidas restringidas al workspace o storage de FIL
4. captura de stdout, stderr y código de salida
5. logging de quién invocó la tool y para qué sesión

Para el MVP, OpenCode debería poder usar solo `domain tools` y no shell abierta.

## Persistencia

Persistencia inicial propuesta:

1. `SQLite`
   Para sesiones, estados, chunks y resultados.

2. `Filesystem local`
   Para audio bruto, fragmentos y exportaciones.

Datos que deben persistirse:

1. sesiones
2. timestamps
3. tipo de sesión
4. transcript chunks
5. prompts enviados a agentes
6. respuestas generadas
7. rutas de audio asociadas
8. invocaciones de tools y sus resultados

## Modelo de sesiones

Tipos iniciales de sesión:

1. `meeting`
2. `dictation`
3. `agent-task`

Estados iniciales de sesión:

1. `created`
2. `running`
3. `stopped`
4. `completed`
5. `failed`

Cada comando relevante debe poder:

1. crear una nueva sesión
2. reutilizar una sesión previa
3. consultar el estado actual

## Estructura de proyecto sugerida

```text
fil/
  cli/
    main.py
    commands/
  application/
    use_cases/
    services/
  domain/
    models/
    enums/
    interfaces/
  tooling/
    registry/
    executor/
    policies/
    adapters/
  infrastructure/
    audio/
    transcription/
    agents/
    storage/
    config/
  shared/
    logging/
    utils/
```

## Responsabilidades por módulo

1. `cli/`
   Define subcomandos, parseo y renderizado de salida.

2. `application/use_cases/`
   Implementa acciones de alto nivel del sistema.

3. `domain/models/`
   Define entidades y tipos de negocio.

4. `domain/interfaces/`
   Define contratos para audio, transcripción, agentes y almacenamiento.

5. `tooling/`
   Define tools, ejecución controlada y políticas.

6. `infrastructure/audio/`
   Implementa captura usando Linux y sus subsistemas de audio.

7. `infrastructure/transcription/`
   Implementa el motor `faster-whisper`.

8. `infrastructure/agents/`
   Implementa el adaptador de OpenCode.

9. `infrastructure/storage/`
   Implementa SQLite y acceso al sistema de archivos.

## Decisiones actuales

Decisiones vigentes para el MVP:

1. lenguaje principal: `Python`
2. interfaz inicial: `CLI por subcomandos`
3. motor de transcripción: `faster-whisper`
4. OpenCode actúa como orquestador y no como dueño del dominio
5. integración de agentes: `opencode run`
6. tools expuestas a OpenCode: solo tools de FIL en el MVP
7. persistencia: `SQLite + filesystem`
8. distribución inicial: entorno local de desarrollo
9. distribución posterior: ejecutable único si el MVP funciona bien

## Escalabilidad

Esta arquitectura permite crecer de forma incremental.

Evoluciones previstas:

1. reemplazar `opencode run` por `serve` sin cambiar los casos de uso
2. cambiar el motor de STT sin tocar la CLI
3. abrir nuevas tools aprobadas para OpenCode
4. agregar un daemon persistente
5. agregar shell interactivo
6. agregar overlay o interfaz gráfica
7. agregar nuevos agentes o tools

La clave es mantener estables los contratos internos y evitar que la lógica de negocio dependa de implementaciones concretas.

## Riesgos conocidos

1. captura simultánea de micrófono y audio del sistema en Linux puede variar según entorno
2. empaquetar `faster-whisper` como binario único puede requerir ajustes de distribución
3. sesiones largas requieren control de almacenamiento y rotación de archivos
4. si OpenCode cambia su interfaz CLI, el adaptador debe aislar ese cambio
5. abrir demasiadas tools del sistema demasiado pronto aumentaría el riesgo operativo

## Decisiones pendientes

Temas aún no cerrados:

1. qué librería exacta se usará para captura de audio
2. si el primer MVP graba por bloques o por stream continuo con ventanas
3. formato exacto de almacenamiento de audio
4. estrategia de resumen y postproceso
5. momento en que se introducirá el daemon persistente
6. conjunto inicial de domain tools expuestas a OpenCode

## Resultado esperado

Si esta arquitectura se respeta, `FIL` podrá empezar como una herramienta pequeña de consola y evolucionar después a una plataforma más completa sin rehacer el núcleo del sistema.
