# Release Notes

## Version Policy

DisMediaPresence uses `major.minor.patch` versioning.

- Patch: documentation updates, bug fixes, small internal maintenance, and compatible corrections.
- Minor: new media sources, new formatting features, new configuration options, and other meaningful feature additions.
- Major: incompatible settings changes, major architecture changes, major UI/application changes, or broad rewrites.

## Release Checklist

- Update package version metadata.
- Update `README.md` version, date, and changelog.
- Update affected files in `docs/`.
- Run tests.
- Verify local install in a virtual environment.
- Build wheel and source distribution artifacts.
- Verify the built wheel installs in a clean virtual environment.
- Commit and push the release changes.
- Tag the release as `vX.Y.Z` and push the tag.

## Artifact Policy

Current releases ship as source plus standard Python package artifacts:

- Source checkout or GitHub source archive from the release tag.
- Python wheel.
- Python source distribution.

Standalone macOS, Windows, or Linux app bundles are not part of current releases. Generated artifacts belong in `dist/` and are ignored by git.

Build artifacts:

```sh
python -m pip install build
python -m build
```

Verify the wheel in a clean virtual environment:

```sh
python3 -m venv /tmp/dmp-release-check
/tmp/dmp-release-check/bin/python -m pip install dist/dis_media_presence-1.1.0-py3-none-any.whl
/tmp/dmp-release-check/bin/dmp version
```

## 1.1.0 - 2026-06-22

- Added Spotify as a configurable source for macOS through Spotify.app automation.
- Added best-effort Spotify detection for Windows media sessions and Linux `playerctl`/MPRIS metadata.
- Added Spotify setup prompts, settings, diagnostics, source-priority integration, and artwork URL support.
- Kept Spotify disabled by default for existing installs.

## 1.0.1 - 2026-06-22

- Rebranded the project, app metadata, documentation, and GitHub links from DisMusicPresence to DisMediaPresence.
- Changed the package distribution name to `dis-media-presence`.
- Added forward-compatible `dis_media_presence` imports while preserving `dis_music_presence`, `dmp`, `dmp.settings`, source keys, and legacy startup templates.

## 1.0.0 - 2026-06-17

- Declared the first stable public release for Apple Music on macOS and Plex through Tautulli or direct Plex API.
- Standardized release packaging around source checkout plus Python wheel and source distribution artifacts.
- Confirmed generated release artifacts are not committed to the repository.

## 0.9.2 - 2026-06-16

- Treated Plex `buffering` sessions as active presence while keeping paused sessions idle.
- Added Plex provider coverage for paused, buffering, remote-client, transcoded, movie, and episode sessions.
- Added Plex artwork fallback coverage for missing or invalid image fields.
- Updated Plex diagnostics wording to report active matching sessions.

## 0.9.1 - 2026-06-16

- Added startup documentation for foreground runs, macOS LaunchAgent, Linux systemd user service, and Windows Task Scheduler setup.
- Added editable startup templates for macOS LaunchAgent and Linux systemd user service.
- Verified editable source install and `dmp` command availability from a fresh virtual environment.

## 0.9.0 - 2026-06-16

- Added source priority commands for showing and setting active-source precedence.
- Added a status command that reports priority order and the current winning source without updating Discord.
- Added an interactive setup command for common Discord, source priority, Apple Music, Plex, and artwork settings.

## 0.8.0 - 2026-06-16

- Added Plex artwork resolution for active Plex playback.
- Added Tautulli image proxy fetching for Plex posters and uploaded those images through the temporary artwork host for Discord.
- Added Plex artwork settings for enablement, preferred image fields, output size, and image format.

## 0.7.0 - 2026-06-16

- Added Plex diagnostics detail for Tautulli and direct Plex API backends.
- Added configured-user session counts and active playback counts to diagnostics.
- Updated Plex setup documentation for troubleshooting and validation.

## 0.6.0 - 2026-06-16

- Added best-effort Apple Music for Windows detection through Windows media sessions.
- Added Windows Apple Music matching configuration.
- Added player-source roadmap notes for generic OS media sessions, Plexamp, VLC, and local webhook input while deferring Spotify.

## 0.5.0 - 2026-06-16

- Changed the default temporary artwork host to Tmpfiles after live Discord validation showed Filebin images can render as a question-mark placeholder.
- Kept Filebin available as an optional artwork provider.
- Removed the explicit music-note character from the default listening format because Discord already shows the listening icon.

## 0.4.0 - 2026-06-16

- Added current Apple Music artwork export through Music.app for Filebin-backed Discord artwork.
- Kept Apple/iTunes catalog artwork as fallback when local Apple Music artwork export is unavailable.
- Added an `artwork.apple_music.enabled` setting for Apple Music artwork export.

## 0.3.0 - 2026-06-16

- Added Apple/iTunes catalog artwork lookup for Apple Music.
- Added Apple catalog fallback when Filebin has no local image path.
- Added Apple catalog settings for enablement, country, and artwork size.

## 0.2.1 - 2026-06-16

- Changed the default artwork provider to Filebin.
- Kept Filebin uploads gated on an explicit local artwork path.

## 0.2.0 - 2026-06-16

- Added optional Discord artwork assets.
- Added custom public artwork URL support.
- Added optional Filebin upload support for local custom artwork with cleanup on shutdown.

## 0.1.2 - 2026-06-16

- Updated Discord Rich Presence payloads to prefer activity details for visible status text where supported.
- Added Discord field-length protection for long formatted presence strings.

## 0.1.1 - 2026-06-16

- Added `plex.user_names` for Plex account and Tautulli display-name aliases.
- Kept `plex.username` as a backward-compatible single-name alias.
- Clarified Plex user matching documentation.

## 0.1.0 - 2026-06-16

- Added the first Python CLI implementation.
- Added local settings management.
- Added Apple Music provider for macOS.
- Added Plex provider through Tautulli or direct Plex server API fallback.
- Added Discord IPC presence updates.
- Added runtime loop, diagnostics, dry-run mode, source probing, and tests.

## 0.0.1 - 2026-06-16

- Added initial project scaffold, license, documentation, ignore rules, and maintainer guidance.
