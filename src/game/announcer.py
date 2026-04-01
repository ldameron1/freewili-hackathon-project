"""Announcer audio pipeline for FREE-WILi playback."""
import os
from pathlib import Path

from elevenlabs.client import ElevenLabs
from freewili import FreeWili

from .audio import (
    CANONICAL_SFX_DIR,
    build_freewili_samples,
    load_audio_config,
    play_uploaded_audio,
    send_and_play_audio,
    upload_audio,
    wav_duration_seconds,
    write_mono_wav,
)
from .state import ANNOUNCER_VOICE_ID

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TMP_TTS_PATH = PROJECT_ROOT / "tmp_tts_latest.wav"


class GameAnnouncer:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        self.toggle = 0
        self.sample_rate = 8000
        self.gain = 1.8
        self.uploaded_sfx = set()
        self.sfx_dir = str(CANONICAL_SFX_DIR)
        self._load_config()

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            print("[TTS] Warning: ELEVENLABS_API_KEY not found.")
            self.client = None
        else:
            self.client = ElevenLabs(api_key=api_key)

    def _load_config(self) -> None:
        try:
            self.sample_rate, self.gain = load_audio_config()
        except Exception as exc:
            print(f"[TTS] Warning: failed to load audio config: {exc}")

    def _build_playback_samples(self, audio_bytes: bytes) -> list[int]:
        return build_freewili_samples(audio_bytes, gain=self.gain, sample_rate=self.sample_rate)

    def _write_wav(self, path: Path, samples: list[int]) -> None:
        write_mono_wav(path, samples, sample_rate=self.sample_rate)

    def speak(self, text: str, voice_id: str = ANNOUNCER_VOICE_ID) -> None:
        if not text.strip():
            return
        if self.client is None:
            print("[TTS Error] ElevenLabs client is not configured.")
            return

        print(f"[TTS] '{text}'")
        try:
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id or ANNOUNCER_VOICE_ID,
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000",
            )
            audio_bytes = b"".join(audio_generator)
            samples = self._build_playback_samples(audio_bytes)
            self._write_wav(TMP_TTS_PATH, samples)

            self.toggle = (self.toggle + 1) % 2
            remote_name = f"tts_{'a' if self.toggle == 0 else 'b'}.wav"
            send_and_play_audio(
                self.fw,
                TMP_TTS_PATH,
                remote_name,
                upload_pause_sec=1.2,
                playback_duration_sec=len(samples) / float(self.sample_rate),
                settle_time_sec=0.5,
            )
        except Exception as exc:
            print(f"[TTS Error] {exc}")

    def play_sfx(self, name: str) -> None:
        local_path = os.path.join(self.sfx_dir, f"{name}.wav")
        remote_name = f"s_{name}.wav"
        if not os.path.exists(local_path):
            return
        try:
            if name not in self.uploaded_sfx:
                upload_audio(
                    self.fw,
                    local_path,
                    remote_name,
                    upload_pause_sec=1.0,
                )
                self.uploaded_sfx.add(name)
            play_uploaded_audio(
                self.fw,
                remote_name,
                playback_duration_sec=wav_duration_seconds(local_path),
            )
        except Exception as exc:
            print(f"[SFX Error] {exc}")

    def announce_phase(self, phase: str, turn: int):
        if phase == "night": self.speak(f"Night {turn} falls. Everyone close your eyes.")
        elif phase == "day_discussion": self.speak(f"Day {turn} breaks. You may discuss.")
        elif phase == "day_vote": self.speak("Time to vote.")

    def announce_death(self, p_name: str, role: str):
        self.speak(f"Tragedy! {p_name} was found dead. They were {role}.")

    def announce_no_death(self):
        self.speak("A miracle! No one died.")

    def announce_eliminated(self, p_name: str, role: str):
        self.speak(f"The town has spoken. {p_name} is eliminated. They were {role}.")

    def announce_game_over(self, winner: str):
        self.speak(f"Game over. The {winner} has won!")
