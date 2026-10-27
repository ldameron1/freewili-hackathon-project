"""Hardware-independent orchestration for human/AI Mafia dialogue."""
from __future__ import annotations

from collections.abc import Callable

UNUSABLE_TRANSCRIPTS = frozenset({
    "[Recording failed or silent]",
    "[Transcription error]",
    "[Silence]",
    "[No API Key]",
})


def run_mafia_dialogue(
    capture_turn: Callable[[int, int], str | None],
    respond: Callable[[str], None],
    *,
    max_turns: int = 3,
) -> int:
    """Run up to max_turns exchanges; a None transcript means RED/end.

    Capture and reply callbacks are supplied by the game engine so this control
    flow can be tested without hardware, Gemini, or ElevenLabs.
    """
    if max_turns < 1:
        raise ValueError("max_turns must be positive")

    exchanges = 0
    for turn_index in range(1, max_turns + 1):
        transcript = capture_turn(turn_index, max_turns)
        if transcript is None:
            break
        statement = transcript.strip()
        if not statement or statement in UNUSABLE_TRANSCRIPTS:
            continue
        respond(statement)
        exchanges += 1
    return exchanges
