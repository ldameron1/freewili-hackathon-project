import os
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from freewili import image as fwi_image

# Constants for Noir-Tech Aesthetic
WIDTH, HEIGHT = 320, 240
COLOR_BG = (10, 10, 15)
COLOR_CRIMSON = (140, 20, 20)
COLOR_TEXT_PRIMARY = (220, 220, 230)
COLOR_TEXT_DIM = (100, 100, 110)
COLOR_ACCENT = (0, 255, 100)  # Terminal Green
COLOR_CARD_BG = (20, 20, 30)
COLOR_CARD_BORDER = (40, 40, 50)

# Path to common Linux fonts
FONT_BOLD = "/usr/share/fonts/truetype/ubuntu/UbuntuSans[wdth,wght].ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/ubuntu/Ubuntu[wdth,wght].ttf"

class HardwareRenderer:
    def __init__(self, temp_dir="/tmp/mafia_ui"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.font_header = ImageFont.truetype(FONT_BOLD, 22)
            self.font_text = ImageFont.truetype(FONT_REGULAR, 16)
            self.font_small = ImageFont.truetype(FONT_REGULAR, 12)
        except:
            print("[UI] Falling back to default fonts")
            self.font_header = ImageFont.load_default()
            self.font_text = ImageFont.load_default()
            self.font_small = ImageFont.load_default()

    def _convert_and_get_path(self, img, name):
        png_path = self.temp_dir / f"{name}.png"
        fwi_path = self.temp_dir / f"{name}.fwi"
        img.save(png_path)
        fwi_image.convert(png_path, fwi_path)
        return str(fwi_path)

    def render_game_screen(self, title, items, turn_info="DAY 1"):
        """Renders the main game loop screen with player list and status."""
        img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
        draw = ImageDraw.Draw(img)

        # 1. Header Bar
        draw.rectangle([0, 0, WIDTH, 35], fill=COLOR_CRIMSON)
        draw.text((10, 5), title.upper(), font=self.font_header, fill=(255, 255, 255))
        draw.text((WIDTH-70, 8), turn_info, font=self.font_small, fill=(255, 255, 255))

        # 2. Player Roster (Max 6 visible per screen usually)
        y = 45
        for item in items[:6]:
            draw.rectangle([10, y, WIDTH-10, y+25], fill=COLOR_CARD_BG, outline=COLOR_CARD_BORDER)
            # Clip text if too long
            display_text = item[:35]
            draw.text((20, y+4), display_text, font=self.font_text, fill=COLOR_TEXT_PRIMARY)
            y += 30

        # 3. Footer indicator
        draw.text((10, HEIGHT-20), "> STATUS: SYNCING...", font=self.font_small, fill=COLOR_ACCENT)
        
        return self._convert_and_get_path(img, "game_screen")

    def render_menu(self, title, items, selected_index=0):
        """Renders the high-contrast hardware menu."""
        img = Image.new('RGB', (WIDTH, HEIGHT), color=COLOR_BG)
        draw = ImageDraw.Draw(img)

        # Header
        draw.rectangle([0, 0, WIDTH, 40], fill=COLOR_CRIMSON)
        draw.text((10, 8), title.upper(), font=self.font_header, fill=(255, 255, 255))

        # List
        y = 50
        for i, item in enumerate(items):
            if i == selected_index:
                # Highlighted bar
                draw.rectangle([0, y, WIDTH, y+24], fill=(60, 20, 20))
                cursor = "> "
                text_color = (255, 255, 255)
            else:
                cursor = "  "
                text_color = COLOR_TEXT_PRIMARY
            
            draw.text((10, y+3), f"{cursor}{item}", font=self.font_text, fill=text_color)
            y += 28

        return self._convert_and_get_path(img, "menu_screen")

    def render_announcement(self, text, type="death"):
        """Full-screen impactful events (Death, Vote Result)."""
        img = Image.new('RGB', (WIDTH, HEIGHT), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Vignette effect
        if type == "death":
            draw.rectangle([0, 0, WIDTH, HEIGHT], fill=(40, 0, 0)) # Red tint
            title = "ELIMINIATED"
            color = (255, 50, 50)
        else:
            title = "NOTIFICATION"
            color = COLOR_ACCENT

        draw.text((WIDTH//2 - 60, 40), title, font=self.font_header, fill=color)
        
        # Center the body text
        lines = text.split('\n')
        y = 100
        for line in lines:
            draw.text((20, y), line, font=self.font_text, fill=(255, 255, 255))
            y += 20

        return self._convert_and_get_path(img, f"announce_{type}")
