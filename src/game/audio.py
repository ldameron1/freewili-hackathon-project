"""Shared audio helpers for the FREE-WILi host runtime.

The display CPU is strict about playback inputs, so the game runtime and the
hardware diagnostics should both go through the same conversion and upload path.
"""
from __future__ import annotations

import json
import math
import struct
import time
import wave
from pathlib import Path

from freewili.types import FreeWiliProcessorType

PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIO_CONFIG_PATH = PROJECT_ROOT / "audio_config.json"
CANONICAL_SFX_DIR = PROJECT_ROOT / "src" / "assets" / "sfx"

DISPLAY_AUDIO_DIR = "/sounds"
DEFAULT_GAIN = 1.8
DEFAULT_SAMPLE_RATE = 8000
ELEVENLABS_PCM_SAMPLE_RATE = 16000


def load_audio_config(config_path: Path = AUDIO_CONFIG_PATH) -> tuple[int, float]:
    """Load the small runtime tuning surface for FREE-WILi playback."""
    sample_rate = DEFAULT_SAMPLE_RATE
    gain = DEFAULT_GAIN

    if not config_path.exists():
        return sample_rate, gain

    with config_path.open("r", encoding="ascii") as config_file:
        config = json.load(config_file)

    if config.get("sample_rate") == ELEVENLABS_PCM_SAMPLE_RATE:
        sample_rate = ELEVENLABS_PCM_SAMPLE_RATE
    gain = float(config.get("gain", DEFAULT_GAIN))
    return sample_rate, gain


def build_freewili_samples(
    audio_bytes: bytes,
    gain: float = DEFAULT_GAIN,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> list[int]:
    """Convert ElevenLabs 16 kHz PCM into the WAV format that playback expects."""
    pcm16 = struct.unpack(f"{len(audio_bytes) // 2}h", audio_bytes)
    limited = [int(math.tanh((sample / 32768.0) * gain) * 32767) for sample in pcm16]

    if sample_rate == ELEVENLABS_PCM_SAMPLE_RATE:
        playback_samples = list(limited)
    else:
        playback_samples = limited[::2]

    fade_len = min(int(sample_rate * 0.02), len(playback_samples))
    for index in range(fade_len):
        fade = index / fade_len if fade_len else 1.0
        playback_samples[index] = int(playback_samples[index] * fade)
        playback_samples[-(index + 1)] = int(playback_samples[-(index + 1)] * fade)

    padding = [0] * int(sample_rate * 0.15)
    return padding + playback_samples + padding


def write_mono_wav(path: Path, samples: list[int], sample_rate: int = DEFAULT_SAMPLE_RATE) -> None:
    """Persist mono 16-bit PCM samples to disk."""
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack(f"{len(samples)}h", *samples))


def sound_path(filename: str) -> str:
    """Return the display-processor upload target for a sound basename."""
    return f"{DISPLAY_AUDIO_DIR}/{filename}"


def wav_duration_seconds(path: str | Path) -> float:
    """Return the duration of a WAV on disk without reading the whole file."""
    with wave.open(str(path), "rb") as wav_file:
        return wav_file.getnframes() / float(wav_file.getframerate())


def upload_audio(
    fw,
    local_path: str | Path,
    remote_name: str,
    *,
    upload_pause_sec: float,
) -> None:
    """Upload a WAV into the display processor's `/sounds` directory."""
    fw.send_file(
        str(local_path),
        sound_path(remote_name),
        processor=FreeWiliProcessorType.Display,
    ).expect("Upload fail")
    time.sleep(upload_pause_sec)


def play_uploaded_audio(
    fw,
    remote_name: str,
    *,
    playback_duration_sec: float,
    settle_time_sec: float = 0.2,
    stop_audio_first: bool = True,
) -> None:
    """Play a previously uploaded sound by basename only."""
    if stop_audio_first and hasattr(fw, "stop_audio"):
        try:
            fw.stop_audio(processor=FreeWiliProcessorType.Display)
        except Exception:
            pass

    fw.play_audio_file(remote_name, processor=FreeWiliProcessorType.Display).expect("Play fail")
    time.sleep(playback_duration_sec + settle_time_sec)


def send_and_play_audio(
    fw,
    local_path: str | Path,
    remote_name: str,
    *,
    upload_pause_sec: float,
    playback_duration_sec: float,
    settle_time_sec: float = 0.2,
    stop_audio_first: bool = True,
) -> None:
    """Upload a WAV to the display processor and play it by basename."""
    upload_audio(fw, local_path, remote_name, upload_pause_sec=upload_pause_sec)
    play_uploaded_audio(
        fw,
        remote_name,
        playback_duration_sec=playback_duration_sec,
        settle_time_sec=settle_time_sec,
        stop_audio_first=stop_audio_first,
    )
