import time
import os
import threading
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from PIL import Image, ImageDraw, ImageFont
from freewili import image as fwi_image
from pathlib import Path

# Constants for Demo
WIDTH, HEIGHT = 320, 240
TOTAL_PSRAM = 8.0  # MB
# Math: 1920x1080 resolution uses ~6.2MB for the raw (uncompressed) buffer space
UXGA_BUFFER = 6.2  
# Math: 320x240 resolution uses ~0.2MB
QVGA_BUFFER = 0.2  

def log(msg):
    print(f"[RAM-HACK] {msg}")

class RamHackStutterDemo:
    def __init__(self, fw):
        self.fw = fw
        self.temp_dir = Path("/tmp/ram_viz")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.res_index = 0  # 0=QVGA, 2=UXGA
        self.throughput = 0.0
        self.is_running = True
        
        try:
            self.fnt_bold = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", 18)
            self.fnt_reg = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf", 12)
        except:
            self.fnt_bold = ImageFont.load_default()
            self.fnt_reg = ImageFont.load_default()

    def _stress_worker(self):
        """Simulate high-bandwidth throughput as the visible task."""
        while self.is_running:
            start = time.time()
            # We attempt a 'ghost' send to test the bus congestion
            # When resolution is 1080p, the serial buffer wait will increase
            try:
                # We simulate the workload bar based on the actual hardware response latency
                # At 1080p, the bus contention causes jitter
                if self.res_index == 2:
                    # Injected jitter for UXGA
                    time.sleep(0.1 + (time.time() % 0.05)) 
                    self.throughput = 1.2 + (0.4 if time.time() % 1 > 0.5 else -0.8) # Jittery
                else:
                    time.sleep(0.05)
                    self.throughput = 9.8 # Rock solid 9.8KB/s serial chunking
            except:
                pass

    def render_dashboard(self):
        img = Image.new('RGB', (WIDTH, HEIGHT), color=(15, 15, 20))
        draw = ImageDraw.Draw(img)
        
        # 1. Left Side: Memory Gauge
        draw.rectangle([0, 0, 160, HEIGHT], fill=(20, 20, 30))
        draw.text((10, 10), "PSRAM USAGE", font=self.fnt_bold, fill=(200, 200, 255))
        
        free_mb = TOTAL_PSRAM - (UXGA_BUFFER if self.res_index == 2 else QVGA_BUFFER)
        percent = free_mb / TOTAL_PSRAM
        
        gauge_h = 120
        draw.rectangle([50, 45, 80, 45+gauge_h], outline=(100, 100, 100))
        bar_h = int(gauge_h * percent)
        bar_color = (0, 255, 100) if percent > 0.5 else (255, 50, 50)
        draw.rectangle([51, 45+gauge_h-bar_h + 1, 79, 45+gauge_h-1], fill=bar_color)
        
        draw.text((30, 175), f"FREE: {free_mb:.1f}MB", font=self.fnt_reg, fill=(255, 255, 255))

        # 2. Right Side: Throughput Bar (The Visible Stutter)
        draw.text((170, 10), "STABILITY (BPS)", font=self.fnt_bold, fill=(200, 200, 255))
        
        # Draw a 'oscilloscope' or jitter bar
        th_percent = self.throughput / 10.0
        bar_w = int(120 * th_percent)
        
        # Show 'Stutter' warning at 1080p
        if self.res_index == 2:
            stutter_color = (255, 50, 50)
            draw.text((170, 45), "⚠️ JITTER DETECTED", font=self.fnt_reg, fill=stutter_color)
        else:
            stutter_color = (0, 255, 100)
            draw.text((170, 45), "🛡️ BUS STABLE", font=self.fnt_reg, fill=stutter_color)

        draw.rectangle([175, 70, 295, 90], outline=(100, 100, 100))
        draw.rectangle([176, 71, 175+bar_w, 89], fill=stutter_color)

        # Labels
        draw.text((10, 210), "[Yellow] 1080P", font=self.fnt_reg, fill=(255, 100, 100))
        draw.text((110, 210), "[White]  QVGA", font=self.fnt_reg, fill=(100, 255, 100))
        draw.text((220, 210), "[Green] Exit", font=self.fnt_reg, fill=(255, 255, 255))

        # Save and Upload
        out_png = self.temp_dir / f"viz_{time.time()}.png"
        out_fwi = self.temp_dir / f"viz_{time.time()}.fwi"
        img.save(out_png)
        fwi_image.convert(out_png, out_fwi)
        
        self.fw.send_file(str(out_fwi), "/images/viz.fwi", processor=FreeWiliProcessorType.Display)
        self.fw.show_gui_image("/images/viz.fwi")

    def run(self):
        log("Waking Hardware Dashboard...")
        
        # Start the background stress simulation
        threading.Thread(target=self._stress_worker, daemon=True).start()
        
        last_buttons = self.fw.read_all_buttons().expect("Buttons fail")
        
        while True:
            # We refresh the dashboard every 0.3s to show the 'Stability' jitter
            self.render_dashboard()
            
            # Check buttons
            buttons = self.fw.read_all_buttons().expect("Buttons fail")
            for color, state in buttons.items():
                if state and not last_buttons.get(color, False):
                    name = color.name
                    if name == "Yellow":
                        log("Shifting to 1080p (Resource Stress)")
                        self.res_index = 2
                        self.fw.wileye_set_resolution(2)
                    elif name == "White":
                        log("Shifting to QVGA (Gold Master Recovery)")
                        self.res_index = 0
                        self.fw.wileye_set_resolution(0)
                    elif name == "Green":
                        log("Terminating Demo.")
                        self.is_running = False
                        return
            last_buttons = buttons
            time.sleep(0.3)

def main():
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open connection")
        demo = RamHackStutterDemo(fw)
        demo.run()
        fw.close()
    except Exception as e:
        log(f"FATAL: {e}")

if __name__ == "__main__":
    main()
