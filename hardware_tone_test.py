import math
import struct
import time
import wave
from pathlib import Path

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

TMP_TONE = Path("/tmp/freewili_tone.wav")
REMOTE_TONE = "/sounds/tone.wav"

def main():
    print("--- DEFINITIVE UPLOAD & PLAY TEST ---")
    fw = None
    try:
        fw = FreeWili.find_first().expect("No device")
        fw.open().expect("Open fail")
        print("Connected!")
        
        # 1. Create a 1s 440Hz WAV
        print(f"Creating {TMP_TONE}...")
        sample_rate = 8000
        duration = 1.0
        frequency = 440.0
        frames = bytearray()
        for i in range(int(sample_rate * duration)):
            val = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            frames.extend(struct.pack("h", val))
        with wave.open(str(TMP_TONE), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(sample_rate)
            f.writeframes(bytes(frames))

        # 2. Upload into /sounds
        print(f"Uploading {TMP_TONE.name} to Display CPU sounds dir...")
        fw.send_file(str(TMP_TONE), REMOTE_TONE, processor=FreeWiliProcessorType.Display).expect("Upload fail")
        time.sleep(1.0)

        # 3. Play from /sounds by basename
        print("Commanding playback of 'tone.wav'...")
        res = fw.play_audio_file("tone.wav", processor=FreeWiliProcessorType.Display)
        if res.is_ok():
            print("SUCCESS: Play command accepted. Listen!")
            time.sleep(3)
        else:
            print(f"FAILURE: {res.err_value}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if fw is not None:
            try:
                fw.close()
            except Exception:
                pass

if __name__ == "__main__":
    main()
