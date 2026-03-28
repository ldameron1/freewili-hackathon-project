"""ElevenLabs TTS integration for AI agents and game announcer."""
import os
import time
import json
import struct
import wave
from typing import Iterator

from elevenlabs.client import ElevenLabs
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from .state import ANNOUNCER_VOICE_ID

CONFIG_PATH = "audio_config.json"

class GameAnnouncer:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        self.toggle = 0
        self.sample_rate = 16000 # Default
        self.gain = 1.8
        self.uploaded_sfx = set()
        
        # Base path for local assets
        self.sfx_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "sfx")
        
        # Load persistent config if exists
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r') as f:
                    config = json.load(f)
                    self.sample_rate = config.get("sample_rate", 16000)
                    self.gain = config.get("gain", 1.8)
            except Exception:
                pass

        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        self.client = ElevenLabs(api_key=api_key)

    def save_config(self):
        with open(CONFIG_PATH, 'w') as f:
            json.dump({"sample_rate": self.sample_rate, "gain": self.gain}, f)

    def speak(self, text: str, voice_id: str = ANNOUNCER_VOICE_ID) -> None:
        """Stream TTS audio directly to the default PyAudio output device."""
        if not text.strip():
            return

        voice_id = voice_id or ANNOUNCER_VOICE_ID
        print(f"[TTS] Streaming voice {voice_id} at {self.sample_rate}Hz: '{text}'")
        try:
            # Fetch PCM from ElevenLabs
            # ElevenLabs supports 16000, 22050, 44100.
            # We always request 16000 and downsample if our target is lower.
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000"
            )
            audio_bytes = b"".join(audio_generator)

            # --- VOLUME BOOST & DOWNSAMPLE ---
            fmt = f"{len(audio_bytes) // 2}h"
            samples = list(struct.unpack(fmt, audio_bytes))
            
            import math
            # GAIN (Soft Clipping): Use tanh to smoothly limit loud peaks and avoid digital clipping crackles
            if self.gain != 1.0:
                boosted = [int(math.tanh((s / 32768.0) * self.gain) * 32767) for s in samples]
            else:
                boosted = samples
            
            # If our target rate is 8000, we drop every other sample from the 16000 source
            if self.sample_rate == 8000:
                final_samples = boosted[::2]
                final_rate = 8000
            else:
                final_samples = boosted
                final_rate = self.sample_rate

            # ANTI-POP LOGIC: Add zero-padding (silence) and fade to avoid embedded speaker pop/clicks
            pad_len = int(final_rate * 0.15) # 150ms of silence
            fade_len = int(final_rate * 0.02) # 20ms fade
            
            for i in range(min(fade_len, len(final_samples))):
                fade_factor = i / fade_len
                final_samples[i] = int(final_samples[i] * fade_factor)
                
            for i in range(min(fade_len, len(final_samples))):
                fade_factor = i / fade_len
                final_samples[-(i+1)] = int(final_samples[-(i+1)] * fade_factor)
                
            final_samples = [0] * pad_len + final_samples + [0] * pad_len

            final_bytes = struct.pack(f"{len(final_samples)}h", *final_samples)
            
            # Save to tmp as WAV
            tmp_path = "tmp_tts_latest.wav"
            with wave.open(tmp_path, "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(final_rate)
                f.writeframes(final_bytes)

            # Rotate tts_a/tts_b
            self.toggle = (self.toggle + 1) % 2
            target_name = f"tts_{'a' if self.toggle == 0 else 'b'}.wav"
            target_path = f"/sounds/{target_name}"

            self.fw.send_file(tmp_path, target_path, processor=FreeWiliProcessorType.Display).expect("Failed to upload TTS")
            time.sleep(0.1)
            
            if hasattr(self.fw, 'stop_audio'):
                self.fw.stop_audio(processor=FreeWiliProcessorType.Display)
                
            self.fw.play_audio_file(target_name, processor=FreeWiliProcessorType.Display).expect("Failed to play TTS file")
            
            # Calculate playback duration and BLOCK to prevent serial interrupt starvation/clicking
            # Adding an extra ~0.5s padding to let the amplifier gracefully complete
            audio_duration = len(final_samples) / final_rate
            time.sleep(audio_duration + 0.5)
            
        except Exception as e:
            print(f"[TTS Error] {e}")

    def play_sfx(self, name: str) -> None:
        """Play a pre-synthesized SFX file from the assets directory."""
        local_path = os.path.join(self.sfx_dir, f"{name}.wav")
        remote_path = f"/sounds/sfx_{name}.wav"
        
        if not os.path.exists(local_path):
            print(f"[SFX Error] Missing local asset: {local_path}")
            return

        try:
            # Upload if not already seen in this session
            if name not in self.uploaded_sfx:
                print(f"[SFX] Uploading {name} to hardware...")
                self.fw.send_file(local_path, remote_path, processor=FreeWiliProcessorType.Display).expect("SFX Upload fail")
                self.uploaded_sfx.add(name)
            
            print(f"[SFX] Playing: {name}")
            self.fw.play_audio_file(f"sfx_{name}.wav", processor=FreeWiliProcessorType.Display).expect("SFX Play fail")
            
            # Simple duration estimation for blocking (SFX are usually short)
            with wave.open(local_path, 'rb') as wav:
                duration = wav.getnframes() / wav.getframerate()
                time.sleep(duration + 0.2)
        except Exception as e:
            print(f"[SFX Error] {e}")

    def announce_phase(self, phase: str, turn: int):
        if phase == "night":
            self.play_sfx("night_bell")
            # Try cold storage for Night 1
            if turn == 1 and os.path.exists(os.path.join(self.sfx_dir, "narrator_night_1.wav")):
                self.play_sfx("narrator_night_1")
            else:
                self.speak(f"Night {turn} falls on the town. Everyone, close your eyes.")
        elif phase == "day_discussion":
            self.play_sfx("morning_bell")
            # Try cold storage for Day 1
            if turn == 1 and os.path.exists(os.path.join(self.sfx_dir, "narrator_day_1.wav")):
                self.play_sfx("narrator_day_1")
            else:
                self.speak(f"Day {turn} breaks. The town awakens. You may now discuss.")
        elif phase == "day_vote":
            if os.path.exists(os.path.join(self.sfx_dir, "narrator_vote_start.wav")):
                self.play_sfx("narrator_vote_start")
            else:
                self.speak("Discussion time is over. It is time to vote.")
            
    def announce_death(self, player_name: str, role: str):
        self.play_sfx("gunshot")
        self.speak(f"Tragedy has struck. {player_name} was found dead this morning. They were a {role}.")
        
    def announce_no_death(self):
        if os.path.exists(os.path.join(self.sfx_dir, "narrator_miracle.wav")):
            self.play_sfx("narrator_miracle")
        else:
            self.speak("A miracle! No one died in the night.")
        
    def announce_eliminated(self, player_name: str, role: str):
        self.speak(f"The town has spoken. {player_name} is eliminated. They were a {role}.")
        
    def announce_game_over(self, winner: str):
        self.speak(f"The game is over. The {winner} has won!")

