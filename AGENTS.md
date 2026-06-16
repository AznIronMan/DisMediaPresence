# AGENTS.md

This file defines repository rules for human operators and AI coding agents working on DisMusicPresence.

## Project Identity

- Project name: DisMusicPresence
- Maintainer: Street Kings Productions
- Company: Clark & Burke LLC
- Website: https://www.cnb.llc
- Developer email: streetkings@cnb.llc
- Current version: `0.0.1`

## Required Workflow

- Every implementation request must be tracked with a `DMP-xxxx` item before code or documentation changes begin.
- This applies to requests from a developer, operator, Codex, Grok, or any other LLM/automation agent.
- Use `.tasks/active/`, `.tasks/pending/`, `.tasks/completed/`, and `.tasks/cancelled/` for local tracking.
- `.tasks/` is intentionally gitignored. Do not reference DMP ticket IDs in public docs, release notes, or README content.
- Increment the project version for every completed change according to semantic versioning.
- Update `README.md` and relevant files in `docs/` when behavior, setup, configuration, usage, or support policy changes.
- At the end of completed changes, commit the work and push `main` to the configured git remote unless the operator explicitly says not to push.

## Versioning Rules

- Patch: documentation changes, bug fixes, small internal maintenance, and compatible corrections.
- Minor: new media sources, new formatting features, new configuration options, and other meaningful feature additions.
- Major: incompatible settings changes, major architecture changes, major UI/application changes, or broad rewrites.
- Keep the root `README.md` version and changelog aligned with project changes.

## Documentation Rules

- Public user-facing documentation belongs in `docs/`.
- The root `README.md` should stay high level: purpose, current status, versioning, usage/fork rules, documentation links, and changelog.
- Do not document internal DMP ticket IDs outside `.tasks/`.
- Refer to `dmp.settings` as the local settings file. Do not document its internal storage format.

## Dependency Rules

- Do not vendor third-party dependencies into the repository.
- Declare dependencies in project metadata and installation documentation when they are added.
- Ignore local dependency folders, virtual environments, generated build output, caches, logs, settings, and secrets.

## Implementation Direction

- Planned primary runtime: Python CLI.
- Planned first source: Apple Music on macOS.
- Planned Plex source: Tautulli API.
- Planned future sources may include Spotify and Linux media-player equivalents.
- Presence formatting should be configurable and should not be unnecessarily hard-coded.
