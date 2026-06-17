# DisMusicPresence

Version: `0.6.0`
Last updated: `2026-06-16`

DisMusicPresence is a local presence bridge for Discord. It reads active playback from Apple Music, Plex, and future media sources, then publishes configurable Discord presence text such as:

- `Listening to Artist - Song`
- `Watching Movie Name`
- `Watching Show Name - S01E02 - Episode Name`

The project is developed by Street Kings Productions, a Clark & Burke LLC company, for internal use first. It is open to the public for use, study, forks, and builds.

## Current Status

`0.6.0` is the current application build-out. It includes:

- Python CLI package with `dmp` command.
- Local settings file named `dmp.settings`.
- Configurable listening and watching format templates.
- Apple Music source provider for macOS.
- Best-effort Apple Music source provider for Windows through Windows media sessions.
- Plex source provider through Tautulli or direct Plex server API fallback.
- Discord local IPC integration with connect, update, clear, and diagnostic behavior.
- Optional Discord artwork assets from a public custom URL, Tmpfiles-uploaded local image, Tmpfiles-uploaded current Apple Music artwork, Filebin, or Apple/iTunes catalog lookup.
- Automatic Apple Music artwork export through Music.app when temporary artwork hosting is enabled and no local artwork path is configured.
- Apple/iTunes catalog fallback when local Apple Music artwork export is unavailable.
- Runtime loop with source priority, polling, dry-run mode, and shutdown cleanup.
- Unit tests using Python standard library `unittest`.

Windows and Linux are not primary test targets yet. Plex support is platform-neutral. Apple Music on Windows is best-effort, untested, and unsupported until validated on a Windows machine with Apple Music installed.

## Quick Start

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
dmp config init
dmp config set discord.client_id YOUR_DISCORD_APPLICATION_CLIENT_ID
dmp diagnostics
dmp run
```

For macOS Apple Music only, the default source settings are enough once Discord is configured. For Plex, enable and configure either Tautulli or direct Plex server API settings.

## Project Rules

- Keep source attribution and license notices intact when using, forking, or redistributing this project.
- Do not vendor third-party dependencies into this repository. Dependencies should be declared in project metadata and documentation when added.
- Keep local secrets, tokens, settings, logs, caches, and generated build output out of git.
- Public documentation should track user-visible behavior by version number.
- Changes should use semantic versioning: `major.minor.patch`.

## Versioning

This project started at `0.0.1`.

- Patch changes: documentation updates, bug fixes, small internal maintenance, and compatible behavior fixes.
- Minor changes: new sources, new formatting features, new configuration options, and other meaningful feature additions.
- Major changes: broad rewrites, major user interface changes, incompatible configuration changes, or major application architecture changes.

The first stable public release can be tagged as `1.0.0` once the core bridge behavior is complete enough for regular use.

## Documentation

User-facing documentation lives in `docs/`:

- [Project Overview](docs/project-overview.md)
- [Installation](docs/installation.md)
- [Configuration](docs/configuration.md)
- [Usage](docs/usage.md)
- [Player Sources](docs/player-sources.md)
- [Contributing](docs/contributing.md)
- [Release Notes](docs/release.md)

## Changelog

### 0.6.0 - 2026-06-16

- Added best-effort Apple Music for Windows detection through Windows media sessions.
- Added Windows Apple Music matching configuration.
- Added player-source roadmap notes for generic OS media sessions, Plexamp, VLC, and local webhook input while deferring Spotify.

### 0.5.0 - 2026-06-16

- Changed the default temporary artwork host to Tmpfiles after live Discord validation showed Filebin images can render as a question-mark placeholder.
- Kept Filebin available as an optional artwork provider.
- Removed the explicit music-note character from the default listening format because Discord already shows the listening icon.

### 0.4.0 - 2026-06-16

- Added current Apple Music artwork export through Music.app for Filebin-backed Discord artwork.
- Kept Apple/iTunes catalog artwork as fallback when local Apple Music artwork export is unavailable.
- Added an `artwork.apple_music.enabled` setting for Apple Music artwork export.

### 0.3.0 - 2026-06-16

- Added Apple/iTunes catalog artwork lookup for Apple Music tracks.
- Kept Filebin as the default artwork provider, with Apple catalog fallback when no local Filebin artwork path is configured.
- Added Apple catalog settings for enablement, country, and artwork size.

### 0.2.1 - 2026-06-16

- Changed default artwork provider to Filebin while keeping uploads disabled until `artwork.filebin.path` is configured.

### 0.2.0 - 2026-06-16

- Added optional artwork settings for Discord Rich Presence large image assets.
- Added custom public artwork URL support.
- Added optional Filebin upload support for local custom artwork images with cleanup on shutdown.

### 0.1.2 - 2026-06-16

- Updated Discord Rich Presence payloads so visible status text prefers the formatted media details where supported.
- Added Discord field-length protection to avoid rejected presence updates for long track or episode names.

### 0.1.1 - 2026-06-16

- Added clearer Plex user match naming with `plex.user_names` for comma- or pipe-separated aliases.
- Kept `plex.username` as a backward-compatible single-name alias.
- Updated Plex documentation for cases where Tautulli shows a display name that differs from the Plex account name.

### 0.1.0 - 2026-06-16

- Added Python CLI package, settings management, configurable format templates, Discord IPC integration, runtime loop, diagnostics, and tests.
- Added Apple Music source support for macOS.
- Added Plex source support through Tautulli or direct Plex server API fallback with configured user matching.
- Updated installation, configuration, usage, contribution, and release documentation.

### 0.0.1 - 2026-06-16

- Created initial project documentation, license, ignore rules, and maintainer guidance.
- Defined planned bridge scope for Apple Music, Plex/Tautulli, Discord presence formatting, and future player sources.
