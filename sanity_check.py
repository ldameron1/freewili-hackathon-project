
import time
import sys
import os
import subprocess
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

def log(msg):
    print(f"[*] {msg}")

def main():
    try:
        log("Finding FreeWili...")
        fw = FreeWili.find_first().expect("No device found")
        fw.open().expect("Failed to open")
        log("Connected to FreeWili.")

        # 1. Change Wristband Color (Radio Signal)
        log("Sending radio signal to change wristband color (Red)...")
        if hasattr(fw, 'select_radio'):
            fw.select_radio(1)
            # Placeholder for 'Set All Red' command based on DEV_HISTORY.md
            fw.write_radio(b'\xFF\xFF\x00\x00'*10)
            log("Radio signal sent.")
        else:
            log("Radio not found on this device.")

        # 2. Capture Photo with FreeWili (WilEye)
        log("Capturing photo with FreeWili camera...")
        fw.wileye_take_picture(0, "wileye_sanity_check.jpg")
        time.sleep(2)
        log("FreeWili photo captured to device SD (wileye_sanity_check.jpg).")

        # 3. Capture Photo with Laptop Camera (using ffmpeg)
        log("Capturing photo with laptop camera...")
        try:
            subprocess.run([
                "ffmpeg", "-y", "-f", "video4linux2", "-i", "/dev/video0", 
                "-frames:v", "1", "laptop_sanity_check.jpg"
            ], check=True, capture_output=True)
            log("Laptop photo captured (laptop_sanity_check.jpg).")
        except Exception as e:
            log(f"Failed to capture laptop photo: {e}")

        # 4. Play Audio on FreeWili
        log("Playing test tone on FreeWili...")
        fw.play_audio_tone(880, 1.0, 0.5)
        
        # 5. Record Audio with Laptop Mic (using ffmpeg)
        log("Recording audio with laptop mic for 3 seconds...")
        try:
            # Note: alsa/pulse might vary. Assuming default.
            subprocess.run([
                "ffmpeg", "-y", "-f", "alsa", "-i", "default", "-t", "3", "laptop_mic_test.wav"
            ], check=True, capture_output=True)
            log("Laptop audio recorded (laptop_mic_test.wav).")
        except Exception as e:
            log(f"Failed to record laptop audio: {e}")

        fw.close()
        log("Sanity check complete.")

    except Exception as e:
        log(f"Error: {e}")

if __name__ == "__main__":
    main()
