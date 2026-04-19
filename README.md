# FIL

FIL es un asistente local para Linux orientado a reuniones, dictado y automatización por comandos.

La idea del proyecto es correr como una herramienta liviana, local-first, que pueda escuchar audio del sistema y del micrófono, transcribir en tiempo casi real y despachar acciones a agentes mediante comandos simples.

En el modelo actual, `FIL` es la plataforma que conoce el dominio de reuniones y `OpenCode` es el orquestador que decide cómo usar tools y agentes sobre ese dominio.

## Objetivo

Construir una interfaz tipo consola para controlar flujos como:

```text
/listen
/dictate
/do "resume esta reunión"
/stop
/status
```

FIL busca resolver tres necesidades principales:

1. Grabar reuniones desde una PC Linux.
2. Transcribir audio localmente con buena privacidad.
3. Ejecutar acciones de agente a partir de comandos cortos.

## Enfoque

FIL no parte de una interfaz gráfica pesada. El enfoque inicial es una plataforma de consola con un daemon local que mantenga procesos vivos en segundo plano.

Esto permite:

1. Menor complejidad en Linux.
2. Mejor control del audio local.
3. Integración futura con overlays, atajos globales o interfaces flotantes.

## Capacidades esperadas

En su primera versión, FIL debería poder:

1. Escuchar micrófono y audio del sistema.
2. Transcribir por bloques usando un motor local.
3. Guardar audio, texto y metadatos de cada sesión.
4. Aceptar comandos estilo slash.
5. Ejecutar acciones como resumir, extraer tareas o dictar notas.

## Stack Tentativo

Componentes base sugeridos:

1. Linux con `PipeWire` o `PulseAudio` para captura de audio.
2. `faster-whisper` para transcripción local.
3. `Python` para orquestación inicial.
4. `SQLite` para metadatos e historial.
5. CLI propia para interacción con el usuario.
6. `OpenCode` como motor opcional de agentes y orquestación.

## Integración con OpenCode

FIL puede usar OpenCode como backend de agentes sin depender de automatización de teclado o de una ventana interactiva.

La relación entre ambos componentes queda definida así:

1. `FIL` es dueño de la captura de audio, sesiones, transcripciones, almacenamiento y tools del dominio.
2. `OpenCode` recibe contexto desde FIL, razona sobre la tarea y orquesta acciones.
3. `OpenCode` no debe ser dueño directo del sistema de audio ni de la persistencia principal.
4. `FIL` define qué tools están disponibles para OpenCode y bajo qué restricciones.

Comandos confirmados por `opencode --help` que resultan relevantes para el proyecto:

1. `opencode run [message..]`
   Ejecuta OpenCode con un mensaje. Es la base más simple para el MVP y encaja bien con comandos como `/do`.

2. `opencode serve`
   Inicia un servidor headless. Es una buena base para una versión con daemon local y llamadas persistentes.

3. `opencode acp`
   Inicia el servidor ACP. Es una opción más fuerte para una futura arquitectura multiagente.

4. `opencode agent`
   Permite gestionar agentes. Es relevante para inspeccionar o preparar agentes especializados.

5. `opencode attach <url>`
   Permite adjuntarse a un servidor OpenCode ya corriendo. Puede ser útil si FIL delega trabajo a una instancia persistente.

Flags especialmente útiles para integración:

1. `-m, --model`
   Permite fijar el modelo usado por una invocación.

2. `-c, --continue`
   Permite continuar la última sesión.

3. `-s, --session`
   Permite continuar una sesión específica.

4. `--prompt`
   Permite fijar un prompt base o de sistema para la ejecución.

Decisión de arquitectura actual:

1. `v1`: usar `opencode run` desde subprocess para comandos puntuales.
2. `v2`: evaluar `opencode serve` o `opencode acp` para un runtime persistente.

## Tools y Orquestación

FIL no debe tratar a OpenCode solo como un generador de texto. Debe tratarlo como un orquestador capaz de invocar tools CLI.

Eso implica:

1. FIL expone tools propias del dominio, por ejemplo iniciar escucha, detener escucha, consultar una sesión o resumir una transcripción.
2. OpenCode orquesta esas tools usando el contexto de la sesión activa.
3. El acceso a herramientas públicas del sistema debe estar controlado y no quedar abierto por defecto.
4. Toda ejecución de tools debe poder registrarse para auditoría y depuración.

## Arquitectura Inicial

FIL puede dividirse en cuatro capas:

1. `CLI`
   Recibe comandos del usuario y muestra resultados.

2. `Daemon local`
   Mantiene el estado de grabación, escucha y transcripción.

3. `Servicios`
   Manejan captura de audio, STT, almacenamiento y acciones.

4. `Agentes`
   Ejecutan tareas de alto nivel como resumir, clasificar o responder instrucciones.

## Comandos de Referencia

Ejemplos del modelo de interacción esperado:

```text
/listen                # inicia escucha/transcripción
/dictate               # graba una nota por voz
/do "extrae tareas"    # ejecuta una acción de agente
/stop                  # detiene el proceso activo
/status                # muestra el estado actual
/history               # lista sesiones previas
```

Ejemplos de cómo FIL podría delegar en OpenCode:

```text
/do "resume esta reunión"
/do "@reviewer extrae riesgos de esta transcripción"
/do "@planner convierte estas notas en plan de acción"
```

## Privacidad

FIL está pensado como una herramienta `local-first`.

Principios base:

1. El audio debe procesarse localmente siempre que sea posible.
2. Las transcripciones deben almacenarse localmente por defecto.
3. Las integraciones externas deben ser opcionales.

## Estado

Actualmente FIL está en etapa de definición y diseño inicial.

La meta del MVP es validar este flujo:

1. Iniciar escucha.
2. Capturar audio local.
3. Transcribir en bloques.
4. Guardar el resultado.
5. Ejecutar una acción simple sobre la transcripción.
6. Delegar una instrucción puntual a OpenCode usando `opencode run`.

## Visión

A futuro, FIL podría extenderse con:

1. Atajos globales.
2. Ventana flotante.
3. Integración con calendarios.
4. Resúmenes automáticos por reunión.
5. Puentes con otros agentes o herramientas externas.
