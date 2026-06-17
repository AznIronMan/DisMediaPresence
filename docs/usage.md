# Usage

## Initialize Settings

```sh
dmp config init
```

Set the Discord application client ID:

```sh
dmp config set discord.client_id YOUR_DISCORD_APPLICATION_CLIENT_ID
```

Open the guided setup menu:

```sh
dmp setup
```

## Check Diagnostics

```sh
dmp diagnostics
```

Diagnostics report whether settings exist, Discord IPC is available, and each source is configured, disabled, unsupported, or unavailable. Secrets are not printed.

## Check Status

```sh
dmp status
```

Status reports the app version, settings path, Discord availability, configured source priority, each provider's current activity, and the source that would win without publishing an update to Discord.

## Probe Sources

Poll enabled sources once without updating Discord:

```sh
dmp probe
```

## Set Source Priority

When more than one source is active, the first active source in `app.source_priority` wins.

Show the current order:

```sh
dmp priority
```

Make Plex win over Apple Music:

```sh
dmp priority set plex,apple_music
```

Make Apple Music win over Plex:

```sh
dmp priority set apple_music,plex
```

## Run The Bridge

```sh
dmp run
```

Run once and exit:

```sh
dmp run --once
```

Run without updating Discord:

```sh
dmp run --dry-run
```

For regular startup at login, see [Startup](startup.md).

Discord may still show the registered application name as the Rich Presence app label. DisMusicPresence sends the formatted media text as the activity details and asks Discord to use details for the visible status text where supported. Long media text is shortened before sending because Discord limits Rich Presence text fields.

## Artwork

Tmpfiles is the default artwork provider. If no local artwork path is configured, Apple Music tracks export the current Music.app artwork and upload it to Tmpfiles. If local artwork is unavailable, Apple Music tracks use Apple/iTunes catalog artwork when a match is found.

Use a public custom artwork URL:

```sh
dmp config set artwork.provider custom_url
dmp config set artwork.custom_url https://example.com/artwork.png
```

Use temporary hosting for a local custom image:

```sh
dmp config set artwork.provider tmpfiles
dmp config set artwork.upload.path .private/artwork.png
```

Tmpfiles uploads are temporary public files and expire automatically. DisMusicPresence cannot delete Tmpfiles uploads after upload.

Filebin remains available if explicitly selected, but live Discord validation showed Filebin-hosted images may render as a question-mark placeholder:

```sh
dmp config set artwork.provider filebin
```

Disable automatic Apple Music artwork export:

```sh
dmp config set artwork.apple_music.enabled false
```

Use only Apple/iTunes catalog artwork:

```sh
dmp config set artwork.provider apple_catalog
```

## Publish A Test Presence

```sh
dmp test-presence
```

This requires Discord to be running and `discord.client_id` to be configured.

## Apple Music Notes

Apple Music support is validated on macOS. If macOS asks for automation permission, allow the terminal or app host running DisMusicPresence to control Music.

Apple Music on Windows is best-effort, untested, and unsupported until validated on a Windows machine with Apple Music installed. It depends on Windows 10 version 1809 or newer and on Apple Music publishing metadata to Windows media sessions.

Paused or stopped Apple Music playback does not publish stale listening presence.

## Plex Notes

Plex support can use Tautulli or direct Plex server API.

For Tautulli:

```sh
dmp config set plex.enabled true
dmp config set plex.provider auto
dmp config set plex.user_names YOUR_PLEX_NAME,YOUR_TAUTULLI_DISPLAY_NAME
dmp config set tautulli.url http://YOUR_TAUTULLI_HOST:8181
dmp config set tautulli.api_key YOUR_TAUTULLI_API_KEY
```

For direct Plex server API:

```sh
dmp config set plex.enabled true
dmp config set plex.provider plex
dmp config set plex.user_names YOUR_PLEX_NAME
dmp config set plex.url http://YOUR_PLEX_HOST:32400
dmp config set plex.token YOUR_PLEX_TOKEN
```

Use `plex.user_names` for every name that may identify the same Plex user. For example, if Plex shows `AznIronMan` but Tautulli session activity shows `Geoff`, set `plex.user_names` to `AznIronMan,Geoff`.

Movies format as `Watching Movie Name`. TV episodes format as `Watching Show Name - SxxExx - Episode Name`.

When artwork is enabled with the default `tmpfiles` provider, Plex sessions attach item artwork to Discord presence. Tautulli-backed sessions use Tautulli's Plex image proxy; direct Plex API sessions use the Plex server image endpoint.

Use diagnostics when Plex is configured but Discord does not update:

```sh
dmp diagnostics
```

The Plex detail lines show whether Tautulli or the direct Plex API is reachable, how many active sessions were found, how many match the configured user, and how many are currently playing.
