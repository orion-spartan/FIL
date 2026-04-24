# Quick Start

Guia rapida para instalar y ejecutar `FIL` en otra PC Linux.

## Requisitos

`FIL` hoy esta orientado a Linux y depende de herramientas locales de audio.

Necesitas:

1. `Python 3.11+`
2. `ffmpeg`
3. `pw-record` (normalmente provisto por PipeWire)
4. `pactl`
5. `wl-copy` o `xsel` para copiar transcripciones al portapapeles
6. `opencode` solo si quieres insights automaticos en `listen live`

Comprueba que existen en la maquina:

```bash
python3 --version
ffmpeg -version
pw-record --version
pactl info
```

## Instalacion

Clona el repositorio e instala el paquete dentro de un entorno virtual.

```bash
git clone <URL_DEL_REPO>
cd FIL

python3 -m venv .venv
source .venv/bin/activate

pip install -U pip
pip install -e .
```

## Verificar

Comprueba que la CLI quedo instalada:

```bash
fil --help
```

Deberias ver estos comandos:

```text
status
do
dictate
talk
watch
sessions
listen
```

## Primer uso

### Estado actual

```bash
fil status
```

### Dictado rapido desde microfono

Graba desde el microfono, transcribe localmente y copia el resultado al portapapeles.

```bash
fil dictate
```

### Modo interactivo corto

Ideal para comandos o frases breves.

```bash
fil talk
```

Controles:

1. `Espacio`: iniciar o detener captura
2. `q`: salir

### Escucha simple

Inicia una sesion de grabacion sencilla:

```bash
fil listen start
```

Detenla con:

```bash
fil listen stop
```

### Reunion en vivo con transcripcion

Si todavia no instalaste `opencode`, arranca sin insights:

```bash
fil listen live --summary-mode off
```

Si ya tienes `opencode`, puedes usar el modo por defecto o fijar uno manual:

```bash
fil listen live --summary-mode auto
```

Controles en vivo:

1. `q`: detener la sesion
2. `i`: pedir un insight manual cuando uses `--summary-mode manual`

## Sesiones y archivos

Los datos de `FIL` se guardan por defecto en:

```text
~/.local/state/fil/
```

Rutas importantes:

1. `~/.local/state/fil/fil.db`: base de datos local
2. `~/.local/state/fil/audio/`: grabaciones simples
3. `~/.local/state/fil/sessions/`: sesiones de reunion y transcripciones
4. `~/.local/state/fil/tmp/`: archivos temporales

Para ver sesiones guardadas:

```bash
fil sessions list
```

Para inspeccionar una sesion:

```bash
fil sessions show <SESSION_ID>
```

## Notas importantes

1. La primera carga de `faster-whisper` puede descargar el modelo si no esta presente.
2. `fil do` todavia no esta conectado al flujo final de agentes; hoy funciona como placeholder.
3. Si `dictate` no puede copiar al portapapeles, instala `wl-copy` o `xsel`.
4. Si falla el audio del sistema, revisa que PipeWire y PulseAudio expongan `pw-record` y `pactl`.

## Problemas comunes

### `ModuleNotFoundError`

Activa el entorno virtual y reinstala dependencias:

```bash
source .venv/bin/activate
pip install -e .
```

### `pw-record` no existe

Instala PipeWire o el paquete de tu distro que provea `pw-record`.

### `pactl` no existe

Instala el paquete de utilidades de PulseAudio que provea `pactl`.

### `opencode failed`

Usa:

```bash
fil listen live --summary-mode off
```

o instala y configura `opencode` en esa PC.
