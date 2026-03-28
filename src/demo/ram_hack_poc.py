import time
import sys
import os
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

def log(msg):
    print(f"[RAM-HACK] {msg}")

def run_stress_test(fw, label):
    """Measures the time and stability of a 2MB upload to the hardware."""
    # Use the 2MB file we generated earlier
    local_file = "/home/ld/Pictures/Hackathon/src/demo/stress_test.bin"
    remote_path = f"/sounds/stress_{label}.bin"
    
    if not os.path.exists(local_file):
        log(f"Error: {local_file} not found. Run 'dd' first.")
        return None

    log(f"Starting Stress Test: {label}...")
    start_time = time.time()
    try:
        # We upload to the WiEye module specifically to test its PSRAM contention
        result = fw.send_file(local_file, remote_path, processor=FreeWiliProcessorType.Display)
        duration = time.time() - start_time
        if result.is_ok():
            log(f" ✅ {label} Upload Success: {duration:.2f}s")
            return duration
        else:
            log(f" ❌ {label} Upload Failed: {result.unwrap_err()}")
            return None
    except Exception as e:
        log(f" ❌ {label} Exception: {e}")
        return None

def main():
    log("Connecting to FREE-WILi...")
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open")
    except Exception as e:
        log(f"Connection failed: {e}")
        return

    # 1. TEST HIGH RESOLUTION (Index 2 = 1080p)
    log("Setting resolution to 1080p (High Memory Usage)...")
    fw.wileye_set_resolution(2)
    time.sleep(2) # Let hardware settle
    
    log("Capture UXGA Sample...")
    fw.wileye_take_picture(2, "uxga_sample.jpg")
    
    high_res_time = run_stress_test(fw, "High-Res")

    # 2. TEST LOW RESOLUTION (Index 0 = 640x480)
    log("Setting resolution to 640x480 (Low Memory Usage)...")
    fw.wileye_set_resolution(0)
    time.sleep(2)
    
    log("Capture VGA Sample...")
    fw.wileye_take_picture(0, "vga_sample.jpg")
    
    low_res_time = run_stress_test(fw, "Low-Res")

    # 3. RESULTS SUMMARY
    log("="*40)
    log("RAM-HACK POC RESULTS")
    log("="*40)
    if high_res_time:
        log(f"UXGA (1080p) Upload: {high_res_time:.2f}s")
    else:
        log(f"UXGA (1080p) Upload: FAILED/TIMEOUT")
        
    if low_res_time:
        log(f"VGA (640x480) Upload: {low_res_time:.2f}s")
    else:
        log(f"VGA (640x480) Upload: FAILED/TIMEOUT")

    if high_res_time and low_res_time:
        delta = high_res_time - low_res_time
        log(f"RAM Savings Gain: {delta:.2f}s faster at low res!")
    
    log("="*40)
    log("Images captured for quality check: uxga_sample.jpg, vga_sample.jpg")
    fw.close()

if __name__ == "__main__":
    main()
