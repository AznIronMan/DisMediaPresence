# Player Sources

DisMusicPresence is built around source providers. A provider reads one media system or player and returns normalized playback data for the shared formatter, artwork resolver, and Discord bridge.

## Current Sources

- Apple Music on macOS through Music.app automation.
- Apple Music on Windows through best-effort Windows media session detection.
- Plex through Tautulli.
- Plex through direct Plex server API fallback.

## Planned Source Direction

Generic OS media sessions are the preferred next expansion path because they can cover multiple players without one custom integration per app.

- Windows media sessions can expose playback metadata from apps that integrate with Windows media controls.
- Linux MPRIS can expose playback metadata from desktop media players over DBus.
- macOS may keep using player-specific integrations where they expose better metadata or artwork.

Plexamp is a strong fit because Plex is already in scope. Prefer a Plex-supported API path if it can identify the active user and current playback cleanly.

VLC is a practical optional source because it has a local HTTP interface, but it requires user-side VLC configuration.

A local webhook source would make the bridge extensible without first-party support for every player. A separate app or script could post normalized playback activity to a local DisMusicPresence endpoint.

Spotify is deferred for now. It remains a future candidate, but it likely needs OAuth and Spotify Web API setup, so it should be handled as a larger dedicated feature.

## Windows Apple Music Status

Apple Music on Windows is best-effort, untested, and unsupported until validated on Windows with Apple Music installed. It depends on Windows 10 version 1809 or newer and on Apple Music publishing title, artist, album, and playback state to Windows media sessions.
