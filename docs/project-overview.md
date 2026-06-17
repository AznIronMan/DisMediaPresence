# Project Overview

DisMusicPresence is a local bridge between media playback sources and Discord presence.

The application polls enabled media sources, normalizes the current activity into a common model, formats that activity with user-configurable templates, and updates Discord through the local IPC interface.

Target presence examples include:

- `Listening to Artist - Song`
- `Watching Movie Name`
- `Watching Show Name - S01E02 - Episode Name`

## Sources

- Apple Music on macOS.
- Apple Music on Windows through best-effort Windows media session detection.
- Plex through Tautulli when available.
- Plex through direct Plex server API when Tautulli is not available.
- Generic OS media sessions, Plexamp, VLC, local webhook input, Spotify, and Linux desktop media players may be added later.

## Source Priority

When multiple sources are enabled, the runtime checks them in configured priority order. The first source with active playback wins for that polling cycle.

Default priority:

```text
apple_music,plex
```

## Discord Output

Discord presence is updated only when the formatted text changes. When no enabled source has active playback, the app clears the previous presence.

The Discord integration requires a Discord application client ID. The app does not bundle or create that application for users.

Optional artwork support can attach a large image asset to Discord Rich Presence. Artwork can come from current Apple Music artwork uploaded to temporary hosting, Apple/iTunes catalog lookup for Apple Music tracks, a public URL, or a local custom image uploaded to temporary public hosting.

## Platform Status

- macOS: primary development platform and Apple Music target.
- Windows: planned compatibility target for Discord and Plex behavior. Apple Music on Windows is best-effort and untested.
- Linux: planned compatibility target for Discord and Plex behavior.

Apple Music is validated on macOS and best-effort on Windows through Windows media sessions. Plex source behavior is designed to be platform-neutral.
