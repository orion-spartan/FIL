# Roadmap Security

## Objetivo

Este documento define el plan de accion de seguridad para `FIL` antes de considerarlo listo para ejecutarse con mas confianza en otra maquina.

La meta no es volver `FIL` perfecto desde el inicio. La meta es reducir primero los riesgos reales de:

1. fuga de transcript o metadatos sensibles
2. ejecucion insegura de procesos externos
3. terminacion accidental de procesos equivocados
4. permisos demasiado abiertos en archivos locales
5. integracion con OpenCode sin controles explicitos

## Criterio de salida minimo

Antes de llamar a `FIL` razonablemente seguro para pruebas fuera de la maquina principal, deberian cumplirse estas condiciones:

1. ningun transcript o prompt sensible viaja por `argv`
2. `FIL` no confia solo en un PID persistido para detener procesos
3. el envio de transcript a OpenCode es explicito y visible para el usuario
4. los archivos de estado, transcript e insights se crean con permisos restrictivos
5. existe al menos una verificacion automatizada de estos controles

## Riesgos actuales

### 1. Exposicion de transcript por linea de comandos

Problema actual:

1. `OpenCodeRunner` pasa el prompt completo a `opencode run` como argumento
2. los insights de `listen live` incluyen texto real de la reunion
3. ese contenido puede quedar visible por `ps`, `/proc/<pid>/cmdline` o tooling local

Impacto:

1. alto para privacidad
2. especialmente riesgoso en maquinas compartidas o corporativas

Archivos relacionados:

1. `fil/infrastructure/agents/opencode_runner.py`
2. `fil/application/services/meeting_service.py`

### 2. Confianza excesiva en PID persistido

Problema actual:

1. `listen stop` carga `recorder_pid` desde SQLite
2. si ese PID existe, FIL envia senales al process group
3. si la base fue alterada o el PID fue reciclado, podria afectarse otro proceso del mismo usuario

Impacto:

1. alto para seguridad operacional local

Archivos relacionados:

1. `fil/application/services/listen_service.py`
2. `fil/infrastructure/storage/session_store.py`
3. `fil/infrastructure/audio/pw_record.py`
4. `fil/shared/process.py`

### 3. Integracion con OpenCode sin politica explicita

Problema actual:

1. `listen live` puede resumir automaticamente con OpenCode
2. el usuario no tiene todavia una capa de politica o consentimiento fuerte
3. no existe todavia una `Tooling Layer` real con controles de ejecucion

Impacto:

1. medio a alto segun el tipo de reunion

Archivos relacionados:

1. `fil/cli/commands/listen.py`
2. `fil/application/services/meeting_service.py`
3. `fil/infrastructure/agents/opencode_runner.py`

### 4. Permisos locales no endurecidos

Problema actual:

1. directorios y archivos sensibles usan permisos por defecto del entorno
2. esto depende de `umask` y de donde apunte `XDG_STATE_HOME`

Impacto:

1. medio

Archivos relacionados:

1. `fil/shared/paths.py`
2. `fil/infrastructure/storage/session_store.py`
3. `fil/application/services/meeting_service.py`

## Plan por fases

## Fase 0: Bloqueadores inmediatos

Objetivo:

1. cerrar los riesgos mas importantes antes de ampliar el uso de `FIL`

Entregables:

1. cambiar `OpenCodeRunner` para enviar prompts por `stdin` o archivo temporal `0600`, nunca por `argv`
2. agregar una advertencia clara cuando una sesion vaya a compartir transcript con OpenCode
3. cambiar el default de `listen live` a `summary_mode=manual` u `off`, o exigir confirmacion explicita para `auto`
4. documentar en `README.md` que `summary_mode=auto` cruza el limite local-first

Validacion:

1. `ps` no debe mostrar fragmentos del transcript ni prompts sensibles
2. el usuario debe ver claramente si una sesion compartira contenido con OpenCode

Prioridad:

1. critica

## Fase 1: Endurecimiento de procesos y estado

Objetivo:

1. evitar que `FIL` interactue con procesos equivocados o con estado local alterado

Entregables:

1. dejar de confiar solo en `recorder_pid` persistido
2. guardar junto al PID informacion adicional para validacion, por ejemplo `start_time`, `command fingerprint` o identificador del runtime
3. preferir manejo con `Popen` vivo cuando el proceso siga en memoria
4. si la identidad del proceso no coincide, marcar la sesion como `failed` y no enviar senales
5. revisar todos los recorders para unificar la logica segura de stop/force_stop

Validacion:

1. una base alterada no debe provocar que `FIL` mate otro proceso no relacionado
2. si hay inconsistencia de PID, `FIL` debe fallar de forma segura

Prioridad:

1. alta

## Fase 2: Permisos y proteccion de datos locales

Objetivo:

1. proteger mejor los artefactos sensibles en disco

Entregables:

1. crear `data_root`, `temp_root` y `sessions_root` con permisos `0700`
2. crear `fil.db`, `transcript.md`, `insights.md` y archivos sensibles con `0600`
3. agregar una verificacion de permisos inseguros al iniciar `FIL`
4. documentar ubicaciones de almacenamiento y expectativas de privacidad
5. definir politica de retencion para audio temporal y transcript intermedio

Validacion:

1. los archivos sensibles no deben quedar world-readable bajo una `umask` permisiva
2. `FIL` debe advertir si detecta permisos inseguros

Prioridad:

1. alta

## Fase 3: Politica de integracion con OpenCode

Objetivo:

1. hacer explicito que datos pueden salir del dominio local y bajo que reglas

Entregables:

1. introducir una politica minima de comparticion para sesiones
2. agregar flags o config como:
   `share_transcript_with_agents`, `allow_remote_summary`, `redact_before_summary`
3. separar resumir localmente de resumir via OpenCode
4. registrar cuando una sesion envio datos a OpenCode y con que modelo
5. preparar una base simple para la futura `Tooling Layer`

Validacion:

1. cada sesion debe dejar trazabilidad clara de si compartio datos con agentes
2. el comportamiento por defecto debe ser conservador

Prioridad:

1. media-alta

## Fase 4: Cobertura automatizada de seguridad

Objetivo:

1. evitar regresiones despues del hardening inicial

Entregables:

1. tests para verificar que `OpenCodeRunner` no expone prompts en `argv`
2. tests para permisos de archivos y directorios
3. tests para rechazo seguro de PID inconsistente
4. tests para defaults conservadores de `listen live`
5. smoke checks documentados para correr en otra maquina

Validacion:

1. cambios de seguridad rompen CI si se revierten accidentalmente

Prioridad:

1. media

## Fase 5: Mejora arquitectonica de largo plazo

Objetivo:

1. alinear la seguridad con la arquitectura declarada del proyecto

Entregables:

1. crear una `Tooling Layer` real con `ToolRegistry`, `ToolExecutor` y `ExecutionPolicy`
2. introducir contratos internos entre `application` e `infrastructure`
3. modelar `AgentTask`, `CommandResult` y eventos de seguridad en dominio
4. centralizar auditoria de invocaciones externas
5. evaluar migrar de `opencode run` a `opencode serve` o `acp` con canal mas controlado

Validacion:

1. OpenCode deja de ser solo un subprocess con texto libre y pasa a integrarse por politica explicita

Prioridad:

1. media

## Orden recomendado de implementacion

1. Fase 0
2. Fase 1
3. Fase 2
4. Fase 4
5. Fase 3
6. Fase 5

La razon de este orden es simple:

1. primero hay que cortar fugas y errores de procesos
2. luego proteger datos locales
3. despues automatizar verificaciones
4. por ultimo refinar la arquitectura completa

## Checklist de salida para ejecutar `FIL` en otra maquina

`FIL` puede considerarse listo para pruebas mas serias cuando este checklist quede completo:

1. prompts y transcripts ya no viajan por argumentos de proceso
2. `summary_mode=auto` no comparte transcript sin decision explicita
3. DB, transcripts, insights y temporales tienen permisos restrictivos
4. stop/cancel de grabadores valida identidad del proceso y falla de forma segura
5. existe al menos una nota visible de privacidad para el usuario
6. existe al menos una bateria minima de tests de seguridad

## Nota final

Hoy `FIL` parece suficientemente seguro para experimentacion local controlada, pero no deberia asumirse todavia como seguro por defecto para maquinas compartidas, reuniones sensibles o entornos corporativos.

Este roadmap define el trabajo minimo para cambiar eso.
