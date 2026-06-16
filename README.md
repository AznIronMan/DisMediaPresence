# DisMusicPresence

Version: `0.0.1`
Last updated: `2026-06-16`

DisMusicPresence is a planned local presence bridge for Discord. The goal is to read what is currently playing in Apple Music, Plex, and potentially other players, then publish a cleaner, configurable Discord presence such as:

- `Listening to ♪ Artist - Song`
- `Watching Movie Name`
- `Watching Show Name - S01E02 - Episode Name`

The project is being developed by Street Kings Productions, a Clark & Burke LLC company, for internal use first. It is open to the public for use, study, forks, and builds.

## Current Status

`0.0.1` is the initial project scaffold. Runtime bridge code has not been added yet.

Planned implementation direction:

- Python CLI application.
- Local settings file named `dmp.settings`.
- Apple Music source support on macOS first.
- Plex source support through Tautulli API.
- Optional future sources for Spotify and Linux media player equivalents.
- Configurable Discord presence formatting instead of hard-coded output.

## Project Rules

- Keep source attribution and license notices intact when using, forking, or redistributing this project.
- Do not vendor third-party dependencies into this repository. Dependencies should be declared in project metadata and documentation when added.
- Keep local secrets, tokens, settings, logs, caches, and generated build output out of git.
- Public documentation should track user-visible behavior by version number.
- Changes should use semantic versioning: `major.minor.patch`.

## Versioning

This project starts at `0.0.1`.

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

## Changelog

### 0.0.1 - 2026-06-16

- Created initial project documentation, license, ignore rules, and maintainer guidance.
- Defined planned bridge scope for Apple Music, Plex/Tautulli, Discord presence formatting, and future player sources.
