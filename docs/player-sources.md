# Player Sources

DisMediaPresence is built around source providers. A provider reads one media system or player and returns normalized playback data for the shared formatter, artwork resolver, and Discord bridge.

## Current Sources

- Apple Music on macOS through Music.app automation.
- Apple Music on Windows through best-effort Windows media session detection.
- Spotify on macOS through Spotify.app automation.
- Spotify on Windows through best-effort Windows media session detection.
- Spotify on Linux through best-effort `playerctl` or MPRIS metadata.
- Plex through Tautulli.
- Plex through direct Plex server API fallback.

## Planned Source Direction

Generic OS media sessions are the preferred next expansion path because they can cover multiple players without one custom integration per app.

- Windows media sessions can expose playback metadata from apps that integrate with Windows media controls.
- Linux MPRIS can expose playback metadata from desktop media players over DBus.
- macOS may keep using player-specific integrations where they expose better metadata or artwork.

Plexamp is a strong fit because Plex is already in scope. Prefer a Plex-supported API path if it can identify the active user and current playback cleanly.

VLC is a practical optional source because it has a local HTTP interface, but it requires user-side VLC configuration.

A local webhook source would make the bridge extensible without first-party support for every player. A separate app or script could post normalized playback activity to a local DisMediaPresence endpoint.

Spotify Web API support remains a future candidate for browser playback and Spotify Connect devices that are not visible through local OS/player integrations. That path likely needs OAuth with PKCE, so it should be handled as a larger dedicated feature.

## Windows Apple Music Status

Apple Music on Windows is best-effort, untested, and unsupported until validated on Windows with Apple Music installed. It depends on Windows 10 version 1809 or newer and on Apple Music publishing title, artist, album, and playback state to Windows media sessions.

## Spotify Platform Status

Spotify is validated first on macOS through the installed Spotify app. Windows support depends on Spotify publishing title, artist, album, and playback state to Windows media sessions. Linux support depends on either `playerctl` or an MPRIS DBus player named `spotify`.
