"""ElevenLabs TTS integration for AI agents and game announcer."""
import os
from typing import Iterator

from elevenlabs.client import ElevenLabs
from elevenlabs import stream

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from .state import ANNOUNCER_VOICE_ID


class GameAnnouncer:
    def __init__(self, fw: FreeWili):
        self.fw = fw
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        self.client = ElevenLabs(api_key=api_key)

    def speak(self, text: str, voice_id: str = ANNOUNCER_VOICE_ID) -> None:
        """Stream TTS audio directly to the default PyAudio output device."""
        if not text.strip():
            return
            
        print(f"[TTS] Streaming voice {voice_id}: '{text}'")
        try:
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )
            # Gather bytes
            audio_bytes = b"".join(audio_generator)
            
            # Save to tmp
            tmp_path = "/tmp/tts.mp3"
            with open(tmp_path, "wb") as f:
                f.write(audio_bytes)
                
            # Upload to FREE-WILi and play natively
            self.fw.send_file(tmp_path, "tts.mp3", FreeWiliProcessorType.Main).expect("Failed to upload TTS")
            self.fw.play_audio_file("tts.mp3").expect("Failed to play TTS file")
            
        except Exception as e:
            print(f"[TTS Error] {e}")

    def announce_phase(self, phase: str, turn: int):
        if phase == "night":
            self.speak(f"Night {turn} falls on the town. Everyone, close your eyes.")
        elif phase == "day_discussion":
            self.speak(f"Day {turn} breaks. The town awakens. You may now discuss.")
        elif phase == "day_vote":
            self.speak("Discussion time is over. It is time to vote.")
            
    def announce_death(self, player_name: str, role: str):
        self.speak(f"Tragedy has struck. {player_name} was found dead this morning. They were a {role}.")
        
    def announce_no_death(self):
        self.speak("A miracle! No one died in the night.")
        
    def announce_eliminated(self, player_name: str, role: str):
        self.speak(f"The town has spoken. {player_name} is eliminated. They were a {role}.")
        
    def announce_game_over(self, winner: str):
        self.speak(f"The game is over. The {winner} has won!")
