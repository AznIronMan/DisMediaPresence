# Startup

DisMusicPresence runs as a foreground CLI process by default:

```sh
dmp run
```

For regular use, install from source, run `dmp setup`, confirm `dmp status`, then use one of the startup options below.

## Recommended Checks

Before configuring startup:

```sh
dmp diagnostics
dmp status
dmp run --once --dry-run
```

Create a log directory if your startup method writes logs into the project folder:

```sh
mkdir -p logs
```

Do not put tokens or API keys in startup templates. Keep those in the local `dmp.settings` file.

## macOS LaunchAgent

The repo includes a LaunchAgent template:

```text
examples/macos/com.streetkings.dismusicpresence.plist
```

Copy it into your user LaunchAgents folder and edit every `/ABSOLUTE/PATH/TO/DisMusicPresence` placeholder before loading it:

```sh
mkdir -p ~/Library/LaunchAgents
cp examples/macos/com.streetkings.dismusicpresence.plist ~/Library/LaunchAgents/
open -e ~/Library/LaunchAgents/com.streetkings.dismusicpresence.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.streetkings.dismusicpresence.plist
launchctl enable gui/$(id -u)/com.streetkings.dismusicpresence
launchctl kickstart -k gui/$(id -u)/com.streetkings.dismusicpresence
```

Check status:

```sh
launchctl print gui/$(id -u)/com.streetkings.dismusicpresence
```

Stop and unload:

```sh
launchctl bootout gui/$(id -u)/com.streetkings.dismusicpresence
```

macOS may ask for automation permission when Apple Music metadata is read. If the LaunchAgent cannot read Apple Music, run `dmp status` manually from Terminal first and allow the automation prompt.

## Linux systemd User Service

Linux support is not validated yet, but Plex and Discord IPC are designed to be platform-neutral. The repo includes a user service template:

```text
examples/linux/dismusicpresence.service
```

Copy it into your user service folder and edit every `/ABSOLUTE/PATH/TO/DisMusicPresence` placeholder before enabling it:

```sh
mkdir -p ~/.config/systemd/user
cp examples/linux/dismusicpresence.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dismusicpresence.service
```

Check logs:

```sh
journalctl --user -u dismusicpresence.service -f
```

Stop and disable:

```sh
systemctl --user disable --now dismusicpresence.service
```

## Windows Task Scheduler

Windows Apple Music support is best-effort and untested. Plex plus Discord should be configured the same way as other platforms after source install.

Use Task Scheduler to run the installed `dmp` command at login. Set:

```text
Program: C:\ABSOLUTE\PATH\TO\DisMusicPresence\.venv\Scripts\dmp.exe
Arguments: --settings C:\ABSOLUTE\PATH\TO\DisMusicPresence\dmp.settings run
Start in: C:\ABSOLUTE\PATH\TO\DisMusicPresence
```

Use `dmp status` in PowerShell before creating the scheduled task so configuration problems are visible first.

## Updating

For source installs:

```sh
git pull
python -m pip install -e .
dmp diagnostics
dmp status
```

Restart the startup service after updating.
