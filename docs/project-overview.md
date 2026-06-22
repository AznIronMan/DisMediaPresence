# Project Overview

DisMediaPresence is a local bridge between media playback sources and Discord presence.

The application polls enabled media sources, normalizes the current activity into a common model, formats that activity with user-configurable templates, and updates Discord through the local IPC interface.

Target presence examples include:

- `Listening to Artist - Song`
- `Watching Movie Name`
- `Watching Show Name - S01E02 - Episode Name`

## Sources

- Apple Music on macOS.
- Apple Music on Windows through best-effort Windows media session detection.
- Spotify on macOS through Spotify.app automation.
- Spotify on Windows through best-effort Windows media session detection.
- Spotify on Linux through best-effort `playerctl` or MPRIS metadata.
- Plex through Tautulli when available.
- Plex through direct Plex server API when Tautulli is not available.
- Generic OS media sessions, Plexamp, VLC, local webhook input, Spotify Web API, and additional Linux desktop media players may be added later.

## Source Priority

When multiple sources are enabled, the runtime checks them in configured priority order. The first source with active playback wins for that polling cycle.

Default priority:

```text
apple_music,spotify,plex
```

Use `dmp priority set plex,apple_music,spotify` when Plex should take precedence over Apple Music and Spotify. Use `dmp status` to see the current order and the active source that would win before publishing to Discord.

## Discord Output

Discord presence is updated only when the formatted text changes. When no enabled source has active playback, the app clears the previous presence.

The Discord integration requires a Discord application client ID. The app does not bundle or create that application for users.

Optional artwork support can attach a large image asset to Discord Rich Presence. Artwork can come from current Apple Music artwork uploaded to temporary hosting, Spotify artwork URLs, Apple/iTunes catalog lookup for Apple Music tracks, a public URL, or a local custom image uploaded to temporary public hosting.

## Platform Status

- macOS: primary development platform and Apple Music/Spotify target.
- Windows: planned compatibility target for Discord, Spotify, and Plex behavior. Apple Music and Spotify on Windows are best-effort and untested.
- Linux: planned compatibility target for Discord, Spotify, and Plex behavior.

Apple Music and Spotify are validated on macOS and best-effort on Windows through Windows media sessions. Spotify on Linux is best-effort through `playerctl` or MPRIS metadata. Plex source behavior is designed to be platform-neutral.
