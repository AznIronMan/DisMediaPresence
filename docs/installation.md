# Installation

DisMusicPresence is currently installed from source.

## Requirements

- Python `3.11` or newer.
- Discord desktop client for local rich presence support.
- A Discord application client ID.
- Apple Music on macOS for Apple Music presence.
- Tautulli or Plex server API access for Plex presence.

There are no runtime third-party Python package dependencies in version `0.9.2`.

## Install From Source

```sh
git clone https://github.com/AznIronMan/DisMusicPresence.git
cd DisMusicPresence
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
dmp version
```

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Development Check

```sh
python -m unittest discover -s tests
```

## Regular Startup

After installing and configuring settings, confirm the app can see Discord and your media sources:

```sh
dmp diagnostics
dmp status
dmp run --once --dry-run
```

Startup templates and platform-specific regular-run notes are in [Startup](startup.md).

## Dependency Policy

Third-party dependencies should be installed through the documented package manager or project metadata when added. Dependencies should not be copied or bundled into this repository.

Local virtual environments, dependency folders, generated artifacts, settings files, logs, and caches are ignored by git.
