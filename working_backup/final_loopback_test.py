import time
import os
import pathlib
import sys
import struct
import wave
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from google import genai
from elevenlabs.client import ElevenLabs

# Load Keys
with open(".env", "r") as f:
    env_lines = f.read().splitlines()
    env = {l.split("=")[0]: l.split("=")[1].strip() for l in env_lines if "=" in l}

gemini_key = env.get("GEMINI_API_KEY")
eleven_key = env.get("ELEVENLABS_API_KEY")

def run_final_test():
    print("--- DEFINITIVE PROMPT-SYNC LOOPBACK TEST (16KHZ) ---")
    try:
        fw = FreeWili.find_first().expect("No device")
        fw.open().expect("Open fail")
        print("Connected!")
    except Exception as e:
        print(f"Connection Error: {e}")
        return

    try:
        ser = fw.display_serial
        if not ser: return

        def wait_for(target, timeout=3.0):
            start = time.time()
            buffer = ""
            while time.time() - start < timeout:
                dq = ser.serial_port.data_queue
                while not dq.empty():
                    item = dq.get_nowait()
                    text = item.decode('utf-8', errors='ignore') if isinstance(item, bytes) else str(item)
                    buffer += text
                if target in buffer:
                    return True, buffer
                time.sleep(0.05)
            return False, buffer

        # 1. GENERATE 16KHZ AUDIO
        print("1. Generating 16kHz Test Voice...")
        client_11 = ElevenLabs(api_key=eleven_key)
        test_text = "The town awakens. Night has fallen, and someone has been eliminated."
        audio_gen = client_11.text_to_speech.convert(
            text=test_text,
            voice_id="nPczCjzI2devNBz1zQrb",
            model_id="eleven_multilingual_v2",
            output_format="pcm_16000"
        )
        audio_bytes = b"".join(audio_gen)
        
        with wave.open("voice_16k.wav", "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(16000); f.writeframes(audio_bytes)

        # 2. UPLOAD
        print("2. Uploading voice_16k.wav -> test.wav...")
        fw.send_file("voice_16k.wav", "test.wav", processor=FreeWiliProcessorType.Display).expect("Upload fail")

        # 3. BREAKOUT
        print("3. Breakout to Top Menu...")
        ser.serial_port.send("\x03"); time.sleep(0.5)
        for _ in range(3): ser.serial_port.send("q"); time.sleep(0.1)
        wait_for("Enter Letter:")

        # 4. START PLAYBACK
        print("4. Starting Playback...")
        ser.serial_port.send("a")
        wait_for("Enter Letter:")
        ser.serial_port.send("f")
        wait_for("Enter audio file name")
        ser.serial_port.send("test.wav\n")
        time.sleep(0.2) # Give it a moment to start playing

        # 5. START RECORD (Simultaneously)
        filename = "loop.wav"
        print(f"5. Starting Record -> {filename}...")
        # Since 'f' just started, we are likely still in the menu or it returns immediately
        ser.serial_port.send("r")
        wait_for("Enter File Name")
        ser.serial_port.send(f"{filename}\n")
        
        print("Capturing loopback for 8s...")
        time.sleep(8.0)

        # 6. STOP
        print("6. Stopping...")
        ser.serial_port.send("\n"); time.sleep(0.3)
        ser.serial_port.send("\x03"); time.sleep(0.5)
        ser.serial_port.send("q"); time.sleep(0.5)
        
        # AGGRESSIVE CLEAN
        ser._empty_all()
        if hasattr(ser.serial_port, 'clear'): ser.serial_port.clear()

        # 7. FETCH
        local = "final_captured_loopback.wav"
        if os.path.exists(local): os.remove(local)
        print(f"7. Fetching /{filename}...")
        try:
            res = ser.get_file(f"/{filename}", pathlib.Path(local), None)
            if res.is_ok():
                size = os.path.getsize(local)
                print(f"SUCCESS: {local} is {size} bytes.")
                if size > 1000:
                    print("8. Transcribing with models/gemini-2.5-flash...")
                    client_gen = genai.Client(api_key=gemini_key)
                    audio_file = client_gen.files.upload(file=local)
                    response = client_gen.models.generate_content(
                        model="models/gemini-2.5-flash",
                        contents=["Transcribe this audio exactly.", audio_file]
                    )
                    print(f"\n--- LOOPBACK RESULT ---\n{response.text}\n-----------------------\n")
                    client_gen.files.delete(name=audio_file.name)
            else:
                print(f"FETCH FAILED: {res.err_value}")
        except Exception as e:
            print(f"EXCEPTION: {e}")

    finally:
        fw.close()

if __name__ == "__main__":
    run_final_test()
