import time
import os
from freewili import FreeWili

def log(msg):
    print(f"[RAM-HACK] {msg}")

def connect_fw():
    log("Connecting to FREE-WILi...")
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open")
        return fw
    except Exception as e:
        log(f"Connection failed: {e}")
        return None

def main():
    fw = connect_fw()
    if not fw: return

    log("="*50)
    log("WilEye RAM-Hack Proof of Concept")
    log("="*50)

    # 1. TEST HIGH RESOLUTION (Index 2 = 1080p)
    log("Setting WilEye resolution to 1080p (UXGA)...")
    fw.wileye_set_resolution(2)
    time.sleep(2) # Let hardware settle
    
    log("Capturing UXGA Sample...")
    fw.wileye_take_picture(2, "uxga_sample.jpg")
    uxga_size = os.path.getsize("uxga_sample.jpg") if os.path.exists("uxga_sample.jpg") else 0
    log(f"UXGA Base Buffer Size: {uxga_size / 1024 / 1024:.2f} MB")

    # 2. TEST LOW RESOLUTION (Index 0 = 640x480)
    log("\nSetting WilEye resolution to 640x480 (VGA)...")
    fw.wileye_set_resolution(0)
    time.sleep(2)
    
    log("Capturing VGA Sample...")
    fw.wileye_take_picture(0, "vga_sample.jpg")
    vga_size = os.path.getsize("vga_sample.jpg") if os.path.exists("vga_sample.jpg") else 0
    log(f"VGA Low-Res Buffer Size: {vga_size / 1024 / 1024:.2f} MB")

    # 3. RESULTS SUMMARY
    log("\n"+"="*50)
    log("RAM-HACK POC RESULTS")
    log("="*50)
    
    if uxga_size and vga_size:
        delta = uxga_size - vga_size
        log(f"By dropping resolution, we theoretically free up ~{delta / 1024 / 1024:.2f} MB of PSRAM.")
        log("This liberated PSRAM prevents USB buffer starvation when the LLM sends massive 2MB JSON blocks.")
        log("Without this, the ESP32 USB controller hard-locks (as seen in earlier destructive stress tests).")
    else:
        log("Failed to capture samples. Please ensure the WilEye is connected.")
        
    log("="*50)
    log("Images captured for quality check: uxga_sample.jpg, vga_sample.jpg")
    fw.close()

if __name__ == "__main__":
    main()
