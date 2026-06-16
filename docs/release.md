# Release Notes

## Version Policy

DisMusicPresence uses `major.minor.patch` versioning.

- Patch: documentation updates, bug fixes, small internal maintenance, and compatible corrections.
- Minor: new media sources, new formatting features, new configuration options, and other meaningful feature additions.
- Major: incompatible settings changes, major architecture changes, major UI/application changes, or broad rewrites.

## Release Checklist

- Update package version metadata.
- Update `README.md` version, date, and changelog.
- Update affected files in `docs/`.
- Run tests.
- Verify local install in a virtual environment.
- Commit and push the release changes.

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
