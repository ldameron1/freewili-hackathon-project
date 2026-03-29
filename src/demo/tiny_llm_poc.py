import time
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from .game.keyboard import HardwareKeyboard
from .game.render_utils import HardwareRenderer

# Constants for PSRAM Demonstration
LLM_WEIGHTS_MB = 7.5  # Simulate a 1-bit quantized model
SYSTEM_OVERHEAD_MB = 0.3
RECOVERY_ICON = "🛡️ LOCAL AI ACTIVE"

def log(msg):
    print(f"[TINY-LLM] {msg}")

class TinyLlmPoC:
    def __init__(self, fw):
        self.fw = fw
        self.kb = HardwareKeyboard()
        self.renderer = HardwareRenderer()
        
    def run(self):
        log("Deploying TinyLLM Standalone PoC...")
        
        # 1. Trigger the RAM-HACK (Recovery)
        log("Optimizing PSRAM Bus (QVGA Mode)...")
        self.fw.wileye_set_resolution(0) # QVGA
        time.sleep(1)
        
        # 2. Simulate Allocation
        log(f"Allocating {LLM_WEIGHTS_MB}MB for Weights...")
        # We simulate this on the hardware screen as a 'Resource Lock'
        self.renderer.render_game_screen("LOCAL AI ENGINE", 
                                        [f"Model: TinyLLM-100M", 
                                         f"Weights: {LLM_WEIGHTS_MB}MB Loaded",
                                         f"Bus: 🛡️ STABLE (QVGA)"], 
                                         turn_info="LOCAL")
        time.sleep(2)
        
        # 3. Get User Request via Typewriter
        user_request = self.kb.get_input(self.fw, "ASK LOCAL AI")
        
        # 4. Simulated Inference (Fast local stream)
        log(f"Streaming Local Inference for: {user_request}")
        
        # We simulate the bit-stream feel
        response = f"I am TinyLLM running on your recovered 8MB PSRAM. You asked: '{user_request}'. My logic is now entirely standalone."
        words = response.split()
        current_text = ""
        
        for word in words:
            current_text += word + " "
            # Stream to display with local priority
            self.renderer.render_game_screen("LOCAL INFERENCE", 
                                            [current_text], 
                                             turn_info="LOCAL")
            # Rapid stream simulation (no API delay)
            time.sleep(0.1)
            
        log("Inference Complete.")
        time.sleep(5)

def main():
    try:
        fw = FreeWili.find_first().expect("No FREE-WiLi")
        fw.open().expect("Open fail")
        poc = TinyLlmPoC(fw)
        poc.run()
        fw.close()
    except Exception as e:
        log(f"FATAL: {e}")

if __name__ == "__main__":
    main()
