# OpenCode para orquestación desde otras aplicaciones

## Fuentes oficiales utilizadas

Toda la información proviene de documentación oficial:

- https://opencode.ai/docs/
- https://opencode.ai/docs/cli/
- https://opencode.ai/docs/server/
- https://opencode.ai/docs/acp/
- https://opencode.ai/docs/mcp-servers/
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/config/
- https://opencode.ai/docs/tools/

Además, se contrastó con la salida local de `opencode --help` para validar comandos disponibles en la instalación actual.

---

# Opciones para llamar OpenCode desde otra aplicación

## 1. Subprocess (CLI)

Permite invocarlo como proceso hijo.

```bash
opencode run "analiza este proyecto"
```

Uso:

- Node child_process
- Python subprocess
- Go exec.Command
- Lua jobstart
- Rust Command

Ideal para:

- automatización simple
- pipelines
- workers
- MVP de FIL

---

## 2. Server Mode

```bash
opencode serve
```

Expone OpenCode como servicio.

Arquitectura:

App externa

↓

HTTP/API

↓

OpenCode Server

↓

Agentes / Tools / MCP

Incluye:

- OpenAPI 3.1
- endpoints
- autenticación
- SDKs generables

Ideal para:

- orquestadores
- daemons
- runtimes multiagente
- integración persistente con FIL

---

## 3. ACP (Agent Client Protocol)

```bash
opencode acp
```

Usa:

- JSON RPC
- stdio
- comunicación agente-a-agente

Ideal para:

- editor integrations
- multi-agent systems
- supervisor → worker model
- evolución de FIL hacia un router de agentes

---

## 4. MCP

```bash
opencode mcp add
```

Permite conectar:

- tools
- servicios externos
- protocolos MCP

Ideal para tool ecosystems.

---

# Comandos confirmados en la instalación local

La salida de `opencode --help` confirma que en esta instalación existen estos comandos:

- `opencode run [message..]`
- `opencode serve`
- `opencode acp`
- `opencode agent`
- `opencode attach <url>`
- `opencode mcp`
- `opencode session`

Esto valida que FIL puede apoyarse en integración real con OpenCode y no en automatización de ventana o escritura simulada.

## Flags útiles confirmados

También están confirmados estos flags relevantes para integración:

- `-m, --model`
- `-c, --continue`
- `-s, --session`
- `--prompt`

Estos flags pueden servir para:

- fijar el modelo para una tarea concreta
- continuar sesiones relacionadas con una reunión
- reusar contexto entre invocaciones
- imponer un prompt base para un agente especializado

---

# Agentes específicos

## Sí parece soportado.

## A. Default Agent

Archivo:

opencode.json

```json
{
  "default_agent": "reviewer"
}
```

Luego:

```bash
opencode run "audita este repo"
```

Usaría ese agente.

---

## B. Agent Mentions

Documentación indica:

```text
@reviewer analiza este módulo
```

o:

```text
@security-auditor revisa vulnerabilidades
```

Esto sugiere invocación explícita.

---

## C. Subagents

Documentados oficialmente.

Pueden existir:

- planner
- reviewer
- coder
- security-auditor

y delegarse tareas.

---

## D. ACP Routing (pendiente validar schema exacto)

Probablemente posible:

```json
{
  "agent": "reviewer",
  "task": "analyze repo"
}
```

Validar contra schema ACP.

---

# Arquitectura posible

Supervisor

├── OpenCode planner

├── OpenCode reviewer

├── OpenCode security agent

└── Aggregator

---

# Recomendación

Si es exploración:

Usar:

- opencode run
- subprocess desde FIL

---

Si es serio:

Usar:

- opencode serve
- ACP
- `attach` si existe un servidor persistente

---

Si es multiagente:

Usar:

- Agents
- ACP
- MCP

---

# Recomendación específica para FIL

Para este proyecto, la estrategia sugerida es:

1. `Primera etapa`
   Usar `opencode run` invocado desde la CLI o daemon de FIL.

2. `Segunda etapa`
   Evaluar `opencode serve` para mantener un backend persistente y reducir overhead por invocación.

3. `Tercera etapa`
   Evaluar `opencode acp` si FIL evoluciona a supervisor de múltiples agentes.

Modelo de responsabilidades recomendado:

1. `FIL` mantiene el dominio: audio, sesiones, transcripciones, almacenamiento y tools propias.
2. `OpenCode` orquesta tareas sobre ese dominio.
3. `OpenCode` no debería recibir shell abierta en el MVP.
4. `FIL` debería exponer un conjunto pequeño de tools internas seguras para que OpenCode las use.

Ejemplos conceptuales para FIL:

```bash
opencode run "resume esta transcripción"
opencode run "@reviewer extrae riesgos de esta reunión"
opencode run --prompt "actúa como analista de reuniones" "extrae tareas accionables"
```

## Implicación para tools CLI

Como OpenCode puede trabajar con CLI y tools, FIL debe definir un borde claro de ejecución:

1. `tools internas de FIL`
   Son las primeras candidatas para exposición a OpenCode.

2. `tools externas aprobadas`
   Solo deberían habilitarse de forma controlada, por ejemplo para audio o procesamiento concreto.

3. `shell arbitraria`
   No se recomienda abrirla en el MVP.

Ejemplos de tools del dominio que FIL podría exponer:

- `fil_session_current`
- `fil_session_transcript`
- `fil_listen_start`
- `fil_listen_stop`
- `fil_session_summary`

Esto mantiene a OpenCode como orquestador sin entregarle control irrestricto del sistema.

---

# Pendiente por validar

Confirmar si existe sintaxis oficial tipo:

```bash
opencode run --agent reviewer "task"
```

o equivalente.

Buscar en:

- CLI flags
- ACP schema
- OpenAPI schema
- salida detallada de `opencode run --help`
- salida detallada de `opencode agent --help`

## Pendientes concretos para FIL

1. Confirmar la sintaxis oficial para elegir agente desde CLI.
2. Confirmar cómo conservar contexto por reunión usando `--continue` o `--session`.
3. Decidir si FIL crea una sesión por reunión o una sesión por comando.
