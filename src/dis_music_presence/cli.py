from __future__ import annotations

import argparse
import getpass
import logging
import re
import sys

from . import APP_NAME, __version__
from .discord_ipc import DiscordConfigError, DiscordError, DiscordIpcClient, check_discord
from .formatter import PresenceFormatter
from .models import ActivityKind, MediaActivity, MediaType
from .runtime import PresenceRuntime, build_providers
from .settings import DEFAULT_SETTINGS, SettingsError, init_settings, load_settings, set_setting


SOURCE_ALIASES = {
    "apple": "apple_music",
    "applemusic": "apple_music",
    "apple_music": "apple_music",
    "music": "apple_music",
    "plex": "plex",
    "sp": "spotify",
    "spotify": "spotify",
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    if not hasattr(args, "handler"):
        parser.print_help()
        return 0

    try:
        return args.handler(args)
    except (SettingsError, DiscordError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dmp", description=f"{APP_NAME} CLI")
    parser.add_argument("--settings", default="dmp.settings", help="Path to local settings file.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command")

    version = subparsers.add_parser("version", help="Show the application version.")
    version.set_defaults(handler=_cmd_version)

    config = subparsers.add_parser("config", help="Manage local settings.")
    config_sub = config.add_subparsers(dest="config_command", required=True)
    config_init = config_sub.add_parser("init", help="Create local settings.")
    config_init.add_argument("--force", action="store_true", help="Overwrite existing settings.")
    config_init.set_defaults(handler=_cmd_config_init)
    config_show = config_sub.add_parser("show", help="Show settings with secrets redacted.")
    config_show.set_defaults(handler=_cmd_config_show)
    config_set = config_sub.add_parser("set", help="Set one setting.")
    config_set.add_argument("key", choices=sorted(DEFAULT_SETTINGS), help="Setting key.")
    config_set.add_argument("value", help="Setting value.")
    config_set.set_defaults(handler=_cmd_config_set)
    config_keys = config_sub.add_parser("keys", help="List supported setting keys.")
    config_keys.set_defaults(handler=_cmd_config_keys)

    diagnostics = subparsers.add_parser("diagnostics", help="Check local configuration and source support.")
    diagnostics.set_defaults(handler=_cmd_diagnostics)

    status = subparsers.add_parser("status", help="Show current source priority and active winner.")
    status.set_defaults(handler=_cmd_status)

    probe = subparsers.add_parser("probe", help="Poll enabled sources once without updating Discord.")
    probe.set_defaults(handler=_cmd_probe)

    priority = subparsers.add_parser("priority", help="Show or set source precedence.")
    priority.set_defaults(handler=_cmd_priority_show)
    priority_sub = priority.add_subparsers(dest="priority_command")
    priority_show = priority_sub.add_parser("show", help="Show current source priority.")
    priority_show.set_defaults(handler=_cmd_priority_show)
    priority_set = priority_sub.add_parser("set", help="Set source priority, for example: plex,apple_music")
    priority_set.add_argument("sources", nargs="+", help="Comma- or space-separated source names.")
    priority_set.set_defaults(handler=_cmd_priority_set)

    setup = subparsers.add_parser("setup", help="Open an interactive setup menu.")
    setup.set_defaults(handler=_cmd_setup)

    run = subparsers.add_parser("run", help="Run the presence bridge.")
    run.add_argument("--once", action="store_true", help="Poll once and exit.")
    run.add_argument("--dry-run", action="store_true", help="Print runtime decisions without updating Discord.")
    run.set_defaults(handler=_cmd_run)

    test_presence = subparsers.add_parser("test-presence", help="Publish a short test presence to Discord.")
    test_presence.add_argument("--text", default=f"{APP_NAME} test", help="Text to publish.")
    test_presence.set_defaults(handler=_cmd_test_presence)

    return parser


def _cmd_version(args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def _cmd_config_init(args: argparse.Namespace) -> int:
    path = init_settings(args.settings, force=args.force)
    print(f"Initialized settings: {path}")
    return 0


def _cmd_config_show(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    for key, value in settings.redacted().items():
        print(f"{key}={value}")
    return 0


def _cmd_config_set(args: argparse.Namespace) -> int:
    set_setting(args.settings, args.key, args.value)
    print(f"Updated {args.key}")
    return 0


def _cmd_config_keys(args: argparse.Namespace) -> int:
    for key in sorted(DEFAULT_SETTINGS):
        print(key)
    return 0


def _cmd_diagnostics(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    print(f"Settings: {settings.path}")

    discord = check_discord(settings.get("discord.client_id"))
    discord_state = _state_label(discord.available, discord.configured)
    print(f"Discord: {discord_state} - {discord.message}")

    for provider in build_providers(settings):
        cap = provider.capability()
        source_state = _source_state(cap.enabled, cap.supported, cap.configured)
        print(f"{cap.name}: {source_state} - {cap.message}")
        for line in provider.diagnostics():
            print(f"  {line}")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    formatter = PresenceFormatter(settings)
    providers = build_providers(settings)
    priority = _effective_source_priority(settings, providers)
    discord = check_discord(settings.get("discord.client_id"))
    discord_state = _state_label(discord.available, discord.configured)

    print(f"Version: {__version__}")
    print(f"Settings: {settings.path}")
    print(f"Discord: {discord_state} - {discord.message}")
    print(f"Source priority: {_priority_label(priority)}")

    winner: tuple[str, str] | None = None
    provider_by_name = {provider.name: provider for provider in providers}
    for name in priority:
        provider = provider_by_name.get(name)
        if provider is None:
            print(f"{name}: unavailable - configured source is not available")
            continue
        activity = provider.poll()
        formatted = formatter.format(activity)
        line = formatted.text if formatted else activity.message
        print(f"{name}: {activity.kind.value} - {line}")
        if winner is None and activity.is_active:
            winner = (name, line)

    if winner is None:
        print("Winner: none")
    else:
        print(f"Winner: {winner[0]} - {winner[1]}")
    return 0


def _cmd_probe(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    formatter = PresenceFormatter(settings)
    for provider in build_providers(settings):
        activity = provider.poll()
        formatted = formatter.format(activity)
        line = formatted.text if formatted else activity.message
        print(f"{provider.name}: {activity.kind.value} - {line}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    runtime = PresenceRuntime(settings, dry_run=args.dry_run)
    if args.once:
        print(runtime.tick())
        runtime.shutdown()
        return 0
    runtime.run_forever()
    return 0


def _cmd_test_presence(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    activity = MediaActivity(
        kind=ActivityKind.LISTENING,
        source=APP_NAME,
        media_type=MediaType.MUSIC,
        title=args.text,
        artist="Test",
        player_state="playing",
    )
    presence = PresenceFormatter(settings).format(activity)
    if presence is None:
        raise DiscordConfigError("Could not create test presence.")
    client = DiscordIpcClient(settings.get("discord.client_id"))
    try:
        client.connect()
        client.set_activity(presence)
    finally:
        client.close()
    print(f"Published test presence: {presence.text}")
    return 0


def _cmd_priority_show(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    priority = _effective_source_priority(settings, build_providers(settings))
    print(_priority_label(priority))
    return 0


def _cmd_priority_set(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings)
    providers = build_providers(settings)
    priority = _normalize_source_priority(args.sources, _known_source_names(providers))
    set_setting(settings.path, "app.source_priority", ",".join(priority))
    print(f"Updated source priority: {_priority_label(priority)}")
    return 0


def _cmd_setup(args: argparse.Namespace) -> int:
    settings = load_settings(args.settings, create=True)
    print(f"Settings: {settings.path}")

    while True:
        print()
        print("Setup")
        print("1. Discord")
        print("2. Source priority")
        print("3. Apple Music")
        print("4. Spotify")
        print("5. Plex")
        print("6. Artwork")
        print("7. Show settings")
        print("q. Quit")
        choice = input("Select: ").strip().lower()

        if choice in {"q", "quit", "exit"}:
            return 0
        if choice == "1":
            _setup_discord(settings)
        elif choice == "2":
            _setup_priority(settings)
        elif choice == "3":
            _setup_apple_music(settings)
        elif choice == "4":
            _setup_spotify(settings)
        elif choice == "5":
            _setup_plex(settings)
        elif choice == "6":
            _setup_artwork(settings)
        elif choice == "7":
            for key, value in settings.redacted().items():
                print(f"{key}={value}")
        else:
            print("Unknown selection.")


def _state_label(available: bool, configured: bool) -> str:
    if available:
        return "available"
    if configured:
        return "unavailable"
    return "unconfigured"


def _source_state(enabled: bool, supported: bool, configured: bool) -> str:
    if not enabled:
        return "disabled"
    if not supported:
        return "unsupported"
    if not configured:
        return "unconfigured"
    return "configured"


def _known_source_names(providers: list[object]) -> list[str]:
    return [str(getattr(provider, "name")) for provider in providers]


def _effective_source_priority(settings, providers: list[object]) -> list[str]:
    known = _known_source_names(providers)
    configured = settings.list("app.source_priority", known)
    return _normalize_source_priority(configured, known)


def _normalize_source_priority(values: list[str] | str, known: list[str]) -> list[str]:
    text = ",".join(values) if isinstance(values, list) else values
    raw_parts = [part for part in re.split(r"[\s,>]+", text) if part.strip()]
    normalized: list[str] = []
    known_set = set(known)
    for raw in raw_parts:
        name = _normalize_source_name(raw)
        if name not in known_set:
            raise SettingsError(f"Unknown source {raw!r}. Valid sources: {', '.join(known)}")
        if name not in normalized:
            normalized.append(name)
    for name in known:
        if name not in normalized:
            normalized.append(name)
    if not normalized:
        raise SettingsError("At least one source is required.")
    return normalized


def _normalize_source_name(value: str) -> str:
    token = value.strip().lower().replace("-", "_")
    compact = token.replace("_", "")
    return SOURCE_ALIASES.get(token) or SOURCE_ALIASES.get(compact) or token


def _priority_label(priority: list[str]) -> str:
    return " > ".join(priority)


def _setup_discord(settings) -> None:
    value = _prompt_value("Discord application client ID", settings.get("discord.client_id"))
    _set_if_value(settings, "discord.client_id", value)
    enabled = _prompt_bool("Enable Discord updates", settings.bool("discord.enabled", True))
    _set_if_value(settings, "discord.enabled", _bool_text(enabled))


def _setup_priority(settings) -> None:
    current = _effective_source_priority(settings, build_providers(settings))
    print(f"Current source priority: {_priority_label(current)}")
    print("1. Apple Music first")
    print("2. Spotify first")
    print("3. Plex first")
    print("4. Custom")
    choice = input("Select: ").strip().lower()

    if choice == "1":
        priority = ["apple_music", "spotify", "plex"]
    elif choice == "2":
        priority = ["spotify", "apple_music", "plex"]
    elif choice == "3":
        priority = ["plex", "apple_music", "spotify"]
    elif choice == "4":
        raw = input("Source priority: ").strip()
        priority = _normalize_source_priority(raw, _known_source_names(build_providers(settings)))
    else:
        print("Source priority unchanged.")
        return

    _write_setting(settings, "app.source_priority", ",".join(priority))
    print(f"Updated source priority: {_priority_label(priority)}")


def _setup_apple_music(settings) -> None:
    enabled = _prompt_bool("Enable Apple Music source", settings.bool("apple_music.enabled", True))
    _set_if_value(settings, "apple_music.enabled", _bool_text(enabled))
    timeout = _prompt_value("Apple Music timeout seconds", settings.get("apple_music.timeout_seconds"))
    _set_if_value(settings, "apple_music.timeout_seconds", timeout)
    windows_ids = _prompt_value("Windows Apple Music app IDs", settings.get("apple_music.windows_app_ids"))
    _set_if_value(settings, "apple_music.windows_app_ids", windows_ids)


def _setup_spotify(settings) -> None:
    enabled = _prompt_bool("Enable Spotify source", settings.bool("spotify.enabled", False))
    _set_if_value(settings, "spotify.enabled", _bool_text(enabled))
    timeout = _prompt_value("Spotify timeout seconds", settings.get("spotify.timeout_seconds"))
    _set_if_value(settings, "spotify.timeout_seconds", timeout)
    windows_ids = _prompt_value("Windows Spotify app IDs", settings.get("spotify.windows_app_ids"))
    _set_if_value(settings, "spotify.windows_app_ids", windows_ids)
    linux_names = _prompt_value("Linux Spotify MPRIS player names", settings.get("spotify.linux_player_names"))
    _set_if_value(settings, "spotify.linux_player_names", linux_names)


def _setup_plex(settings) -> None:
    enabled = _prompt_bool("Enable Plex source", settings.bool("plex.enabled", False))
    _set_if_value(settings, "plex.enabled", _bool_text(enabled))
    provider = _prompt_choice("Plex provider", settings.get("plex.provider", "auto"), ["auto", "tautulli", "plex"])
    _set_if_value(settings, "plex.provider", provider)
    user_names = _prompt_value(
        "Plex user aliases (Plex account and Tautulli display names, comma separated)",
        settings.get("plex.user_names") or settings.get("plex.username"),
    )
    _set_if_value(settings, "plex.user_names", user_names)
    user_id = _prompt_value("Plex user ID (optional)", settings.get("plex.user_id"))
    _set_if_value(settings, "plex.user_id", user_id)
    tautulli_url = _prompt_value("Tautulli URL", settings.get("tautulli.url"))
    _set_if_value(settings, "tautulli.url", tautulli_url)
    tautulli_key = _prompt_value("Tautulli API key", settings.get("tautulli.api_key"), secret=True)
    _set_if_value(settings, "tautulli.api_key", tautulli_key)
    plex_url = _prompt_value("Plex server URL", settings.get("plex.url"))
    _set_if_value(settings, "plex.url", plex_url)
    plex_token = _prompt_value("Plex token", settings.get("plex.token"), secret=True)
    _set_if_value(settings, "plex.token", plex_token)


def _setup_artwork(settings) -> None:
    provider = _prompt_choice(
        "Artwork provider",
        settings.get("artwork.provider", "tmpfiles"),
        ["tmpfiles", "custom_url", "apple_catalog", "filebin", "none"],
    )
    _set_if_value(settings, "artwork.provider", provider)
    upload_path = _prompt_value("Local artwork upload path", settings.get("artwork.upload.path"))
    _set_if_value(settings, "artwork.upload.path", upload_path)
    custom_url = _prompt_value("Custom artwork public URL", settings.get("artwork.custom_url"))
    _set_if_value(settings, "artwork.custom_url", custom_url)
    apple_enabled = _prompt_bool("Enable automatic Apple Music artwork", settings.bool("artwork.apple_music.enabled", True))
    _set_if_value(settings, "artwork.apple_music.enabled", _bool_text(apple_enabled))
    spotify_enabled = _prompt_bool("Enable Spotify artwork URLs", settings.bool("artwork.spotify.enabled", True))
    _set_if_value(settings, "artwork.spotify.enabled", _bool_text(spotify_enabled))
    plex_enabled = _prompt_bool("Enable Plex artwork", settings.bool("artwork.plex.enabled", True))
    _set_if_value(settings, "artwork.plex.enabled", _bool_text(plex_enabled))


def _prompt_value(label: str, current: str = "", secret: bool = False) -> str | None:
    current = current or ""
    shown = "<configured>" if secret and current else current
    prompt = f"{label}"
    if shown:
        prompt += f" [{shown}]"
    prompt += ": "
    reader = getpass.getpass if secret else input
    value = reader(prompt).strip()
    if value == "":
        return None
    return value


def _prompt_bool(label: str, current: bool) -> bool:
    default = "Y/n" if current else "y/N"
    value = input(f"{label} [{default}]: ").strip().lower()
    if value == "":
        return current
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    print("Invalid yes/no value. Keeping current value.")
    return current


def _prompt_choice(label: str, current: str, choices: list[str]) -> str | None:
    value = input(f"{label} ({'/'.join(choices)}) [{current}]: ").strip().lower()
    if value == "":
        return None
    if value not in choices:
        print(f"Invalid choice. Keeping {current}.")
        return None
    return value


def _set_if_value(settings, key: str, value: str | None) -> None:
    if value is None:
        return
    _write_setting(settings, key, value)


def _write_setting(settings, key: str, value: str) -> None:
    set_setting(settings.path, key, value)
    settings.values[key] = value


def _bool_text(value: bool) -> str:
    return "true" if value else "false"
