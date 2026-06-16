from __future__ import annotations

import json
import os
import socket
import struct
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from .models import FormattedPresence


OP_HANDSHAKE = 0
OP_FRAME = 1
OP_CLOSE = 2
MAX_ACTIVITY_FIELD_LENGTH = 128
STATUS_DISPLAY_DETAILS = 2


class DiscordError(RuntimeError):
    pass


class DiscordNotRunningError(DiscordError):
    pass


class DiscordConfigError(DiscordError):
    pass


@dataclass(frozen=True)
class DiscordStatus:
    available: bool
    configured: bool
    message: str


class DiscordIpcClient:
    def __init__(self, client_id: str) -> None:
        if not client_id.strip():
            raise DiscordConfigError("discord.client_id is required.")
        self.client_id = client_id.strip()
        self._transport: _Transport | None = None

    def connect(self) -> None:
        transport = _connect_transport()
        self._transport = transport
        self._send(OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
        response = self._recv()
        if response.get("evt") == "ERROR":
            raise DiscordError(_error_message(response))

    def set_activity(self, presence: FormattedPresence, pid: int | None = None) -> None:
        if self._transport is None:
            self.connect()
        activity = build_activity_payload(presence)
        self._rpc("SET_ACTIVITY", {"pid": pid or os.getpid(), "activity": activity})

    def clear_activity(self, pid: int | None = None) -> None:
        if self._transport is None:
            self.connect()
        self._rpc("SET_ACTIVITY", {"pid": pid or os.getpid(), "activity": None})

    def close(self) -> None:
        transport = self._transport
        if transport is None:
            return
        try:
            self._send(OP_CLOSE, {})
        except DiscordError:
            pass
        transport.close()
        self._transport = None

    def _rpc(self, command: str, args: dict[str, object]) -> dict[str, object]:
        payload = {"cmd": command, "args": args, "nonce": str(uuid.uuid4())}
        self._send(OP_FRAME, payload)
        response = self._recv()
        if response.get("evt") == "ERROR":
            raise DiscordError(_error_message(response))
        return response

    def _send(self, op: int, payload: dict[str, object]) -> None:
        if self._transport is None:
            raise DiscordNotRunningError("Discord IPC is not connected.")
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        header = struct.pack("<II", op, len(encoded))
        self._transport.write(header + encoded)

    def _recv(self) -> dict[str, object]:
        if self._transport is None:
            raise DiscordNotRunningError("Discord IPC is not connected.")
        header = self._transport.read_exact(8)
        op, length = struct.unpack("<II", header)
        data = self._transport.read_exact(length)
        if op == OP_CLOSE:
            raise DiscordError("Discord closed the IPC connection.")
        return json.loads(data.decode("utf-8"))


def check_discord(client_id: str) -> DiscordStatus:
    if not client_id.strip():
        return DiscordStatus(False, False, "discord.client_id is not configured.")
    try:
        transport = _connect_transport()
        transport.close()
    except DiscordNotRunningError as exc:
        return DiscordStatus(False, True, str(exc))
    return DiscordStatus(True, True, "Discord IPC socket is available.")


def build_activity_payload(presence: FormattedPresence) -> dict[str, object]:
    details = _activity_details(presence)
    return {
        "type": presence.activity_type,
        "name": _truncate_activity_field(details),
        "details": _truncate_activity_field(details),
        "state": _truncate_activity_field(presence.source),
        "status_display_type": STATUS_DISPLAY_DETAILS,
        "instance": False,
    }


def _activity_details(presence: FormattedPresence) -> str:
    text = presence.text.strip()
    prefixes = {
        2: ("Listening to ",),
        3: ("Watching ",),
    }
    for prefix in prefixes.get(presence.activity_type, ()):
        if text.casefold().startswith(prefix.casefold()):
            return text[len(prefix) :].strip()
    return text


def _truncate_activity_field(value: str) -> str:
    text = value.strip()
    if len(text) <= MAX_ACTIVITY_FIELD_LENGTH:
        return text
    return text[: MAX_ACTIVITY_FIELD_LENGTH - 3].rstrip() + "..."


def _connect_transport() -> "_Transport":
    errors: list[str] = []
    for path in _candidate_ipc_paths():
        try:
            if sys.platform == "win32":
                return _WindowsPipeTransport(path)
            return _UnixSocketTransport(path)
        except OSError as exc:
            errors.append(f"{path}: {exc}")
    detail = "; ".join(errors[:2])
    if detail:
        raise DiscordNotRunningError(f"Discord IPC socket was not found or could not be opened ({detail}).")
    raise DiscordNotRunningError("Discord IPC socket was not found.")


def _candidate_ipc_paths() -> list[str]:
    if sys.platform == "win32":
        return [rf"\\.\pipe\discord-ipc-{index}" for index in range(10)]

    bases = [
        os.environ.get("XDG_RUNTIME_DIR"),
        os.environ.get("TMPDIR"),
        os.environ.get("TMP"),
        os.environ.get("TEMP"),
        "/tmp",
    ]
    paths: list[str] = []
    for base in bases:
        if not base:
            continue
        for index in range(10):
            paths.append(str(Path(base) / f"discord-ipc-{index}"))
    return paths


def _error_message(response: dict[str, object]) -> str:
    data = response.get("data")
    if isinstance(data, dict):
        message = data.get("message")
        if isinstance(message, str):
            return message
    return "Discord IPC returned an error."


class _Transport:
    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def read_exact(self, length: int) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class _UnixSocketTransport(_Transport):
    def __init__(self, path: str) -> None:
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.connect(path)

    def write(self, data: bytes) -> None:
        self.socket.sendall(data)

    def read_exact(self, length: int) -> bytes:
        chunks: list[bytes] = []
        remaining = length
        while remaining:
            chunk = self.socket.recv(remaining)
            if not chunk:
                raise DiscordError("Discord IPC connection closed unexpectedly.")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def close(self) -> None:
        self.socket.close()


class _WindowsPipeTransport(_Transport):
    def __init__(self, path: str) -> None:
        self.pipe: BinaryIO = open(path, "r+b", buffering=0)

    def write(self, data: bytes) -> None:
        self.pipe.write(data)
        self.pipe.flush()

    def read_exact(self, length: int) -> bytes:
        data = self.pipe.read(length)
        if len(data) != length:
            raise DiscordError("Discord IPC connection closed unexpectedly.")
        return data

    def close(self) -> None:
        self.pipe.close()
