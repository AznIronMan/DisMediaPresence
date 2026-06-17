# Configuration

DisMusicPresence uses a local settings file named `dmp.settings`.

Create it with:

```sh
dmp config init
```

Show current settings with secrets redacted:

```sh
dmp config show
```

Update a setting:

```sh
dmp config set discord.client_id YOUR_DISCORD_APPLICATION_CLIENT_ID
```

List supported keys:

```sh
dmp config keys
```

Do not commit `dmp.settings` to git.

## Core Settings

```text
app.poll_interval_seconds
app.source_priority
discord.enabled
discord.client_id
```

Default source priority is:

```text
apple_music,plex
```

## Formatting Settings

```text
format.listening
format.watching_movie
format.watching_episode
```

Default templates:

```text
Listening to {artist} - {title}
Watching {title}
Watching {show_title} - {episode_code} - {episode_title}
```

Available template fields include:

```text
source
player_state
title
artist
album
show_title
season
episode
episode_code
episode_title
```

## Apple Music Settings

```text
apple_music.enabled
apple_music.timeout_seconds
apple_music.windows_app_ids
```

Apple Music is supported on macOS. Apple Music on Windows is best-effort and untested. The Windows path reads Windows media sessions and selects the session that appears to belong to Apple Music. Windows media session support depends on Windows 10 version 1809 or newer.

The first time the app checks Apple Music on macOS, macOS may ask for automation permission.

`apple_music.timeout_seconds` defaults to `10` so macOS automation has enough time to return current track metadata.

`apple_music.windows_app_ids` is a comma-separated list of strings used to identify the Apple Music Windows media session. Override it only if diagnostics show that Apple Music for Windows publishes a different session app id on your machine.

## Artwork Settings

```text
artwork.provider
artwork.custom_url
artwork.custom_text
artwork.upload.path
artwork.filebin.path
artwork.filebin.base_url
artwork.filebin.bin
artwork.filebin.delete_on_shutdown
artwork.tmpfiles.base_url
artwork.apple_music.enabled
artwork.apple_catalog.enabled
artwork.apple_catalog.country
artwork.apple_catalog.size
```

`artwork.provider` supports:

```text
none
custom_url
apple_catalog
tmpfiles
filebin
```

The default provider is `tmpfiles`. If `artwork.upload.path` points to a local image file, that image is uploaded to temporary hosting. If no local path is configured and `artwork.apple_music.enabled` is true, Apple Music tracks export the current Music.app artwork and upload it to temporary hosting. When local artwork is unavailable, Apple Music tracks fall back to Apple/iTunes catalog artwork if `artwork.apple_catalog.enabled` is true.

Use `custom_url` when you already have a public image URL:

```sh
dmp config set artwork.provider custom_url
dmp config set artwork.custom_url https://example.com/artwork.png
dmp config set artwork.custom_text "Custom Artwork"
```

Use `tmpfiles` when you want DisMusicPresence to upload a local custom image to Tmpfiles and use that temporary public URL in Discord:

```sh
dmp config set artwork.provider tmpfiles
dmp config set artwork.upload.path .private/artwork.png
```

Tmpfiles uploads are temporary public files and cannot be deleted by DisMusicPresence after upload.

Use `filebin` only when you explicitly want Filebin hosting:

```sh
dmp config set artwork.provider filebin
dmp config set artwork.upload.path .private/artwork.png
```

Filebin uploads use `https://filebin.net`, a generated bin name, and cleanup on shutdown. If `artwork.filebin.bin` is empty, DisMusicPresence deletes the generated bin during cleanup. If you set a custom bin, DisMusicPresence deletes only the uploaded file so it does not remove unrelated files in the bin. Live Discord testing showed Filebin images may render as a question-mark placeholder in Discord, so `tmpfiles` is the recommended default.

Supported local image types are JPEG, PNG, WebP, and GIF. Keep custom artwork small; DisMusicPresence rejects temporary uploads larger than 10 MB.

Temporary artwork is public while active. Do not upload private, sensitive, or copyrighted images unless you are comfortable with that exposure.

Disable automatic current Apple Music artwork export:

```sh
dmp config set artwork.apple_music.enabled false
```

Use `apple_catalog` when you want only Apple/iTunes catalog artwork and no Filebin fallback:

```sh
dmp config set artwork.provider apple_catalog
```

Apple catalog settings:

```sh
dmp config set artwork.apple_catalog.enabled true
dmp config set artwork.apple_catalog.country US
dmp config set artwork.apple_catalog.size 600
```

## Plex Settings

```text
plex.enabled
plex.provider
plex.user_names
plex.user_id
tautulli.url
tautulli.api_key
plex.url
plex.token
```

`plex.provider` supports:

```text
auto
tautulli
plex
```

Use `auto` to prefer Tautulli when configured and fall back to direct Plex server API when needed.

Configure either `plex.user_names` or `plex.user_id` so the app selects the right user's playback session. This prevents another Plex user's activity from being published.

`plex.user_names` is a comma- or pipe-separated list of names that may identify the same Plex user in different APIs. For example, a Plex account name may be `AznIronMan` while Tautulli displays the active session as `Geoff`; configure both:

```sh
dmp config set plex.user_names AznIronMan,Geoff
```

`plex.username` remains supported as a backward-compatible single-name alias, but `plex.user_names` is preferred.

Example Tautulli setup:

```sh
dmp config set plex.enabled true
dmp config set plex.provider auto
dmp config set plex.user_names YOUR_PLEX_NAME,YOUR_TAUTULLI_DISPLAY_NAME
dmp config set tautulli.url http://YOUR_TAUTULLI_HOST:8181
dmp config set tautulli.api_key YOUR_TAUTULLI_API_KEY
```

Example direct Plex server API setup:

```sh
dmp config set plex.enabled true
dmp config set plex.provider plex
dmp config set plex.user_names YOUR_PLEX_NAME
dmp config set plex.url http://YOUR_PLEX_HOST:32400
dmp config set plex.token YOUR_PLEX_TOKEN
```
