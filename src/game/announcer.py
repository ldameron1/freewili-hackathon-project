"""Announcer audio pipeline for FREE-WILi playback."""
import json
import math
import os
import struct
import time
import wave
from pathlib import Path

from elevenlabs.client import ElevenLabs
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

from .state import ANNOUNCER_VOICE_ID

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "audio_config.json"
TMP_TTS_PATH = PROJECT_ROOT / "tmp_tts_latest.wav"


class GameAnnouncer:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        self.toggle = 0
        self.sample_rate = 8000
        self.gain = 1.8
        self.uploaded_sfx = set()
        self.sfx_dir = os.path.join(os.path.dirname(__file__), "sfx")
        self._load_config()

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            print("[TTS] Warning: ELEVENLABS_API_KEY not found.")
            self.client = None
        else:
            self.client = ElevenLabs(api_key=api_key)

    def _load_config(self) -> None:
        if not CONFIG_PATH.exists():
            return
        try:
            with CONFIG_PATH.open("r", encoding="ascii") as config_file:
                config = json.load(config_file)
            self.sample_rate = 8000 if config.get("sample_rate") != 16000 else 16000
            self.gain = float(config.get("gain", 1.8))
        except Exception as exc:
            print(f"[TTS] Warning: failed to load {CONFIG_PATH.name}: {exc}")

    def _build_playback_samples(self, audio_bytes: bytes) -> list[int]:
        samples = list(struct.unpack(f"{len(audio_bytes) // 2}h", audio_bytes))
        boosted = [
            int(math.tanh((sample / 32768.0) * self.gain) * 32767)
            for sample in samples
        ]

        if self.sample_rate == 8000:
            final_samples = boosted[::2]
        else:
            final_samples = boosted

        fade_len = min(int(self.sample_rate * 0.02), len(final_samples))
        for index in range(fade_len):
            fade_factor = index / fade_len if fade_len else 1.0
            final_samples[index] = int(final_samples[index] * fade_factor)
            final_samples[-(index + 1)] = int(final_samples[-(index + 1)] * fade_factor)

        pad_len = int(self.sample_rate * 0.15)
        return ([0] * pad_len) + final_samples + ([0] * pad_len)

    def _write_wav(self, path: Path, samples: list[int]) -> None:
        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(struct.pack(f"{len(samples)}h", *samples))

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
            remote_path = f"/sounds/{remote_name}"

            self.fw.send_file(str(TMP_TTS_PATH), remote_path, processor=FreeWiliProcessorType.Display).expect(
                "Upload fail"
            )
            time.sleep(1.2)

            if hasattr(self.fw, "stop_audio"):
                try:
                    self.fw.stop_audio(processor=FreeWiliProcessorType.Display)
                except Exception:
                    pass

            self.fw.play_audio_file(remote_name, processor=FreeWiliProcessorType.Display).expect("Play fail")
            time.sleep((len(samples) / float(self.sample_rate)) + 0.5)
        except Exception as exc:
            print(f"[TTS Error] {exc}")

    def play_sfx(self, name: str) -> None:
        local_path = os.path.join(self.sfx_dir, f"{name}.wav")
        remote_name = f"s_{name}.wav"
        remote_path = f"/sounds/{remote_name}"
        if not os.path.exists(local_path):
            return
        try:
            if name not in self.uploaded_sfx:
                self.fw.send_file(local_path, remote_path, processor=FreeWiliProcessorType.Display).expect("SFX fail")
                self.uploaded_sfx.add(name)
                time.sleep(1.0)
            self.fw.play_audio_file(remote_name, processor=FreeWiliProcessorType.Display).expect("SFX play fail")
            with wave.open(local_path, "rb") as wav_file:
                duration = wav_file.getnframes() / float(wav_file.getframerate())
            time.sleep(duration + 0.2)
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
