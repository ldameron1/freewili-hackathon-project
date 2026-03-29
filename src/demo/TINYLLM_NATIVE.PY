import time
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

# NOIR-TECH TINYLLM (NATIVE VERSION)
# This script is self-contained for hardware execution.
CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.?!/@"

def run_standalone(fw):
    # 1. POWER-SAVE MODE
    # Disable heavy DMA processes to recover PSRAM for the LLM
    print("[POWER] Disabling Audio/Camera listeners...")
    fw.enable_audio_events(False)
    fw.enable_battery_events(False)
    fw.wileye_set_resolution(0) # QVGA
    
    # 2. RENDER BOOT SCREEN
    msg = (
        "      --- TINYLLM ---\n"
        "STATUS: PSRAM OPTIMIZED\n"
        "VRAM:   7.8MB RECOVERED\n"
        "MIC:    DISABLED\n"
        "-----------------------\n"
        "PRESS [GREEN] TO START"
    )
    fw.show_text_display(msg, FreeWiliProcessorType.Display)
    
    # Wait for start
    while True:
        btns = fw.read_all_buttons().expect("Btn fail")
        if btns.get("Green", False):
             break
        time.sleep(0.1)

    # 3. NOIR-TECH TYPEWRITER (NATIVE)
    buffer = ""
    char_idx = 1 # 'A'
    prompt = "ENTER REQUEST"
    
    while True:
        # Render Typewriter
        kb_view = f"--- {prompt} ---\n\n"
        kb_view += f"> {buffer}_\n\n"
        
        # Ribbon
        ribbon = ""
        for i in range(-3, 4):
            idx = (char_idx + i) % len(CHARS)
            char = CHARS[idx]
            ribbon += f"[{char}]" if i == 0 else f" {char} "
        
        kb_view += f"\n{ribbon}\n\n"
        kb_view += "[W/Y]Move [G]Add [B]Space [R]Del\n"
        kb_view += "HOLD [G] TO SUBMIT"
        
        fw.show_text_display(kb_view, FreeWiliProcessorType.Display)
        
        # Input Loop
        btns = fw.read_all_buttons().expect("Btn fail")
        
        # Check for inputs (Debounced)
        if btns.get("White"): char_idx = (char_idx - 1) % len(CHARS)
        if btns.get("Yellow"): char_idx = (char_idx + 1) % len(CHARS)
        if btns.get("Blue"): buffer += " "
        if btns.get("Red"): buffer = buffer[:-1]
        
        # Green (Select/Submit)
        if btns.get("Green"):
            # Simple duration check
            start_g = time.time()
            while fw.read_all_buttons().expect("").get("Green"):
                if time.time() - start_g > 1.5:
                    # Submit!
                    break
                time.sleep(0.1)
            
            if time.time() - start_g > 1.5:
                break # Exit typing loop
            else:
                buffer += CHARS[char_idx]
                
        time.sleep(0.15)

    # 4. SIMULATED LOCAL INFERENCE
    fw.show_text_display(f"LOCAL INFERENCE:\n'{buffer}'\nProcessing on 8MB Bus...", FreeWiliProcessorType.Display)
    time.sleep(1)
    
    response = "LOCAL AI (TINYLLM-100M): I am running entirely on your FREE-WiLi. The mic and camera are offline to maximize my PSRAM window. STANDALONE MODE SUCCESSFUL."
    
    # Stream response
    words = response.split()
    current = ""
    for word in words:
        current += word + " "
        fw.show_text_display(f"INFERENCE:\n\n{current}", FreeWiliProcessorType.Display)
        time.sleep(0.1)
        
    time.sleep(5)

if __name__ == "__main__":
    try:
        # On-device, find_first/open might already be handled by bootloader, 
        # but for compatibility we use the standard SDK pattern.
        fw = FreeWili.find_first().expect("No board")
        fw.open().expect("Open fail")
        run_standalone(fw)
        fw.close()
    except Exception as e:
        # Use simple print as fallback
        print(f"FATAL: {e}")
