"""Speech recognition via Gemini audio transcription."""
import os
from google import genai
from google.genai import types

MODELS_FALLBACK = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-flash-latest",
    "models/gemini-flash-lite-latest",
    "models/gemini-3.1-flash-lite-preview",
    "models/gemini-1.5-flash",
]

TRANSCRIPTION_SYSTEM_INSTRUCTION = (
    "Transcribe the speech in the provided audio exactly as spoken. "
    "If there are multiple speakers, identify them as 'Speaker 1:', 'Speaker 2:', etc. "
    "If there is no speech, output '[Silence]'. "
    "Do not describe the audio or repeat these instructions."
)

_PROMPT_ECHO_SNIPPETS = (
    "please transcribe the speech in this audio exactly as you hear it",
    "please provide a complete and accurate transcription of the audio",
    "transcribe this audio exactly",
)

class SpeechTranscriber:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("[Speech] Warning: GEMINI_API_KEY not found in environment.")
        self.client = genai.Client(api_key=self.api_key)
        self.model_index = 0

    @staticmethod
    def _looks_like_prompt_echo(text: str) -> bool:
        normalized = " ".join(text.lower().split())
        return any(snippet in normalized for snippet in _PROMPT_ECHO_SNIPPETS)

    @staticmethod
    def _audio_part(audio_file):
        return types.Part.from_uri(
            file_uri=audio_file.uri,
            mime_type=getattr(audio_file, "mime_type", None),
        )

    def transcribe(self, wav_path: str) -> str:
        """Uploads WAV file and extracts spoken text."""
        if not self.api_key:
            return "[No API Key]"
        audio_file = None
        try:
            print(f"[Speech] Transcribing {wav_path}...")
            audio_file = self.client.files.upload(file=wav_path)

            for _ in range(len(MODELS_FALLBACK)):
                try:
                    model_name = MODELS_FALLBACK[self.model_index]
                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[self._audio_part(audio_file)],
                        config=types.GenerateContentConfig(
                            system_instruction=TRANSCRIPTION_SYSTEM_INSTRUCTION,
                            temperature=0,
                            response_mime_type="text/plain",
                        ),
                    )
                    text = (response.text or "").strip()
                    if not text:
                        raise ValueError(f"Empty transcription response from {model_name}")
                    if self._looks_like_prompt_echo(text):
                        raise ValueError(f"Prompt echo response from {model_name}: {text}")
                    print(f"[Speech] Result ({model_name}): {text}")
                    return text
                except Exception as e:
                    error_str = str(e)
                    recoverable = (
                        ("429" in error_str and "quota" in error_str.lower())
                        or "empty transcription response" in error_str.lower()
                        or "prompt echo response" in error_str.lower()
                    )
                    if recoverable:
                        self.model_index += 1
                        if self.model_index < len(MODELS_FALLBACK):
                            print(
                                f"[Speech] {error_str}. Switching to {MODELS_FALLBACK[self.model_index]}..."
                            )
                            continue
                    raise e

        except Exception as e:
            print(f"[Speech Error] {e}")
            return "[Error transcribing]"
        finally:
            if audio_file is not None:
                try:
                    self.client.files.delete(name=audio_file.name)
                except Exception:
                    pass
