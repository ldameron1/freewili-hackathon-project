import os
import math
import struct
import time
import wave
from pathlib import Path
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

load_dotenv()


def build_freewili_samples(audio_bytes: bytes, gain: float = 1.8) -> list[int]:
    pcm16 = struct.unpack(f"{len(audio_bytes)//2}h", audio_bytes)
    limited = [int(math.tanh((sample / 32768.0) * gain) * 32767) for sample in pcm16]
    downsampled = limited[::2]
    fade_len = min(int(8000 * 0.02), len(downsampled))
    for index in range(fade_len):
        fade = index / fade_len if fade_len else 1.0
        downsampled[index] = int(downsampled[index] * fade)
        downsampled[-(index + 1)] = int(downsampled[-(index + 1)] * fade)
    pad = [0] * int(8000 * 0.15)
    return pad + downsampled + pad
def test_tts():
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=api_key)
    
    text = "This is a hardware diagnostic test of the Eleven Labs and Free Willy audio pipeline."
    print(f"Requesting TTS: '{text}'")
    
    audio_generator = client.text_to_speech.convert(
        text=text,
        voice_id="nPczCjzI2devNBz1zQrb", # Narrator
        model_id="eleven_multilingual_v2",
        output_format="pcm_16000"
    )
    audio_bytes = b"".join(audio_generator)
    print(f"Received {len(audio_bytes)} bytes of PCM data.")

    # Save locally to verify
    local_file = Path("/tmp/test_eleven.wav")
    playback_samples = build_freewili_samples(audio_bytes)
    with wave.open(str(local_file), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(8000)
        f.writeframes(struct.pack(f"{len(playback_samples)}h", *playback_samples))
    
    fsize = os.path.getsize(local_file)
    print(f"Saved to {local_file} ({fsize} bytes)")
    
    if fsize < 1000:
        print("FAIL: Local file is too small.")
        return

    print("Connecting to hardware...")
    try:
        fw = FreeWili.find_first().expect("No device")
        fw.open().expect("Open fail")
        
        target = "test_tts.wav"
        remote_target = f"/sounds/{target}"
        print(f"Uploading {target} to Display CPU...")
        fw.send_file(str(local_file), remote_target, processor=FreeWiliProcessorType.Display).expect("Upload fail")
        time.sleep(1.0)
        
        print("Playing...")
        res = fw.play_audio_file(target, processor=FreeWiliProcessorType.Display)
        if res.is_ok():
            print("SUCCESS: Command accepted.")
            time.sleep(5)
        else:
            print(f"FAILURE: {res.err_value}")
            
    except Exception as e:
        print(f"Hardware Error: {e}")
    finally:
        try: fw.close()
        except: pass

if __name__ == "__main__":
    test_tts()
