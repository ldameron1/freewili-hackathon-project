"""Placeholder for Gemini speech recognition using generateContent with audio part."""
import os
from google import genai
from google.genai import types

MODELS_FALLBACK = [
    "models/gemini-2.5-flash",
    "models/gemini-3.1-flash-lite-preview",
    "models/gemini-2.0-flash",
    "models/gemini-1.5-flash",
]

class SpeechTranscriber:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("[Speech] Warning: GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_index = 0
        
    def transcribe(self, wav_path: str) -> str:
        """Uploads WAV file and extracts spoken text."""
        if not self.api_key:
            return "[No API Key]"
        try:
            print(f"[Speech] Transcribing {wav_path}...")
            # For hackathon, we could use the File API
            audio_file = self.client.files.upload(file=wav_path)
            
            for attempt in range(len(MODELS_FALLBACK)):
                try:
                    model_name = MODELS_FALLBACK[self.model_index]
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[
                            "Please transcribe the speech in this audio exactly as you hear it. If there are multiple speakers, identify them as 'Speaker 1:', 'Speaker 2:', etc. If there is no speech, output '[Silence]'.",
                            audio_file
                        ]
                    )
                    text = response.text.strip()
                    print(f"[Speech] Result ({model_name}): {text}")
                    return text
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str and "quota" in error_str.lower():
                        self.model_index += 1
                        if self.model_index < len(MODELS_FALLBACK):
                            print(f"[Speech] Quota exhausted for {model_name}. Switching to {MODELS_FALLBACK[self.model_index]}...")
                            continue
                    raise e
                    
        except Exception as e:
            print(f"[Speech Error] {e}")
            return "[Error transcribing]"
