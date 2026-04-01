"""Startup helpers for assembling a playable Mafia session."""
from __future__ import annotations

import os

import psutil

from .state import DEFAULT_VOICES, Player, Role

PLAYER_ROLES = [
    Role.MAFIA,
    Role.MAFIA,
    Role.DOCTOR,
    Role.DETECTIVE,
    Role.TOWN,
    Role.TOWN,
    Role.TOWN,
    Role.TOWN,
    Role.TOWN,
]

PLAYER_PERSONALITIES = [
    "The human participant",
    "Analytical and cautious",
    "Boisterous and friendly",
    "Nervous and defensive",
    "Quiet but observant",
    "Aggressive and accusatory",
    "Sarcastic and witty",
    "Helpful and naive",
    "Overthinking everything",
]

PLAYER_NAMES_BY_MODE = {
    "debug": ["User", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"],
    "mixed": ["User", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"],
    "human_only": ["User", "User2", "User3", "User4", "User5", "User6", "User7", "User8", "User9"],
    "ai_only": ["Zeus", "Alice", "Bob", "Charlie", "Dave", "Eve", "Frank", "Grace", "Heidi"],
}

STALE_PROCESS_MARKERS = {
    "src/main.py",
    "hardware_tone_test.py",
    "test_tts_playback.py",
    "tests/test_tts_playback.py",
    "src/utils/cleanup_hw.py",
}


def cleanup_stale_processes() -> None:
    """Kill leftover hardware scripts that keep the serial/audio path busy."""
    current_pid = os.getpid()
    protected_pids = {current_pid}

    try:
        current_process = psutil.Process(current_pid)
        protected_pids.update(parent.pid for parent in current_process.parents())
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            if proc.pid in protected_pids:
                continue

            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(cmdline)
            if "python" not in joined:
                continue
            if any(marker in joined for marker in STALE_PROCESS_MARKERS):
                print(f"[Startup] Terminating stale process {proc.pid}: {joined}")
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue


def build_players_for_mode(mode: str) -> list[Player]:
    """Create the fixed nine-player roster used by the MVP game flow."""
    try:
        names = PLAYER_NAMES_BY_MODE[mode]
    except KeyError as exc:
        raise ValueError(f"Unsupported game mode: {mode}") from exc

    players: list[Player] = []
    for index, (name, role, personality) in enumerate(
        zip(names, PLAYER_ROLES, PLAYER_PERSONALITIES, strict=True)
    ):
        players.append(
            Player(
                name=name,
                role=role,
                is_ai=not name.startswith("User"),
                voice_id=DEFAULT_VOICES[index % len(DEFAULT_VOICES)],
                personality=personality,
            )
        )
    return players
