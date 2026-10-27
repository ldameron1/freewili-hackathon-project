"""Play checked-in narration on FREE-WILi without an ElevenLabs API key.

Run from the repository root on a machine connected to the device:
    python tests/test_cached_audio_playback.py --repeats 3
"""
from __future__ import annotations

import argparse
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from freewili import FreeWili
from src.game.audio import play_uploaded_audio, upload_audio, wav_duration_seconds

DEFAULT_WAV = ROOT / "src/assets/sfx/narrator_day_1.wav"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=DEFAULT_WAV)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if args.repeats < 1:
        parser.error("--repeats must be positive")

    with wave.open(str(args.file), "rb") as src:
        rate = src.getframerate()
        channels = src.getnchannels()
        width = src.getsampwidth()
    if channels != 1 or width != 2:
        parser.error("Expected a mono 16-bit PCM WAV")
    duration = wav_duration_seconds(args.file)
    print(f"WAV: {args.file}, {rate} Hz, expected {duration:.2f}s per playback")
    print("Compare actual audible duration/pitch against the WAV; host sleep is not a measurement.")

    fw = FreeWili.find_first().expect("No FREE-WILi connected")
    fw.open().expect("Open failed")
    try:
        upload_audio(fw, args.file, "diag.wav", upload_pause_sec=1.2)
        for index in range(args.repeats):
            print(f"Playback {index + 1}/{args.repeats} (no TTS API request)")
            started = time.monotonic()
            play_uploaded_audio(
                fw, "diag.wav", playback_duration_sec=duration, settle_time_sec=0.5
            )
            print(f"Host command + wait elapsed: {time.monotonic() - started:.2f}s")
    finally:
        fw.close()


if __name__ == "__main__":
    main()
