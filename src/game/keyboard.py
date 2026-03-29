import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from freewili import image as fwi_image

# Constants for Keyboard
CHARS = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.?!/@"
WIDTH, HEIGHT = 320, 240
COLOR_BG = (10, 10, 15)
COLOR_CRIMSON = (140, 20, 20)
COLOR_TEXT = (220, 220, 230)
COLOR_HIGHLIGHT = (255, 255, 255)

class HardwareKeyboard:
    def __init__(self, temp_dir="/tmp/keyboard"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.buffer = ""
        self.char_index = 1 # Start on 'A'
        
        try:
            self.font_main = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf", 22)
            self.font_kb = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/UbuntuMono-B.ttf", 26)
            self.font_sm = ImageFont.truetype("/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf", 16)
        except:
            self.font_main = ImageFont.load_default()
            self.font_kb = ImageFont.load_default()
            self.font_sm = ImageFont.load_default()

    def _render_and_show(self, fw, prompt):
        img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
        draw = ImageDraw.Draw(img)
        
        # Header
        draw.rectangle([0, 0, WIDTH, 40], fill=COLOR_CRIMSON)
        draw.text((10, 8), "NOIR-TECH TYPEWRITER", font=self.font_main, fill=(255, 255, 255))
        
        # Prompt & Buffer
        draw.text((10, 50), f"{prompt}:", font=self.font_sm, fill=(150, 150, 160))
        # Draw buffer with a cursor
        display_buffer = self.buffer + "_"
        draw.text((15, 80), display_buffer, font=self.font_main, fill=COLOR_TEXT)
        
        # Keyboard Ribbon (Scroller)
        draw.rectangle([0, 160, WIDTH, 210], fill=(30, 30, 40))
        
        # Draw current, prev, next letters
        # Show a 5-char window
        for i in range(-2, 3):
            idx = (self.char_index + i) % len(CHARS)
            char = CHARS[idx]
            x = 160 + (i * 50) - 10
            color = COLOR_HIGHLIGHT if i == 0 else (100, 100, 110)
            draw.text((x, 165), char, font=self.font_kb, fill=color)
            if i == 0:
                # Bracket the middle letter
                draw.rectangle([x-5, 165, x+25, 205], outline=COLOR_CRIMSON, width=2)

        # Legend
        draw.text((10, 215), "[W/Y]Cycle  [G]Add  [B]Space  [R]Del", font=self.font_sm, fill=(100, 100, 110))

        # Convert and Display
        png_path = self.temp_dir / "kb.png"
        fwi_path = self.temp_dir / "kb.fwi"
        img.save(png_path)
        fwi_image.convert(png_path, fwi_path)
        
        remote_path = "/images/keyboard.fwi"
        fw.send_file(str(fwi_path), remote_path, processor=FreeWiliProcessorType.Display)
        fw.show_gui_image(remote_path)

    def get_input(self, fw, prompt="ENTER REQUEST"):
        """Blocking call to get user input from the hardware."""
        self.buffer = ""
        self.char_index = 1
        
        log("Keyboard Active. Awaiting input...")
        last_buttons = fw.read_all_buttons().expect("Buttons fail")
        green_start_time = None
        
        while True:
            self._render_and_show(fw, prompt)
            
            buttons = fw.read_all_buttons().expect("Buttons fail")
            for color, state in buttons.items():
                name = color.name
                is_pressed = state and not last_buttons.get(color, False)
                
                if is_pressed:
                    if name == "White": # UP
                        self.char_index = (self.char_index - 1) % len(CHARS)
                    elif name == "Yellow": # DOWN
                        self.char_index = (self.char_index + 1) % len(CHARS)
                    elif name == "Green": # SELECT (Press)
                        green_start_time = time.time()
                    elif name == "Blue": # SPACE
                        self.buffer += " "
                    elif name == "Red": # DELETE
                        self.buffer = self.buffer[:-1]
                
                # Check for Green Release (Submit logic)
                if not state and last_buttons.get(color, False) and name == "Green":
                    duration = time.time() - green_start_time if green_start_time else 0
                    if duration > 1.5: # Long press
                        log(f"Input submitted: {self.buffer}")
                        return self.buffer
                    else: # Short press
                        self.buffer += CHARS[self.char_index]
                    green_start_time = None
            
            last_buttons = buttons
            time.sleep(0.1)

def log(msg):
    print(f"[KEYBOARD] {msg}")

if __name__ == "__main__":
    # Test script
    try:
        fw = FreeWili.find_first().expect("No FREE-WiLi")
        fw.open().expect("Open fail")
        kb = HardwareKeyboard()
        result = kb.get_input(fw, "TEST INPUT")
        print(f"RESULT: {result}")
        fw.close()
    except Exception as e:
        log(f"FATAL: {e}")
