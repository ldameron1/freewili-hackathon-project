import sys
import os
import time
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

# Canonical files for Gold Master
GOLD_SOUNDS = [
    "sfx_gunshot.wav", "sfx_morning_bell.wav", "sfx_night_bell.wav",
    "sfx_narrator_day_1.wav", "sfx_narrator_game_start.wav",
    "sfx_narrator_mafia_win.wav", "sfx_narrator_miracle.wav",
    "sfx_narrator_night_1.wav", "sfx_narrator_town_win.wav",
    "sfx_narrator_vote_start.wav"
]
GOLD_IMAGES = ["menu.fwi", "game_ui.fwi"]

def log(msg):
    print(f"[CLEANUP] {msg}")

def main():
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open connection")
        
        # 1. Clean Display CPU (ESP32)
        log("Auditing Display CPU (ESP32)...")
        for dir_path, gold_list in [("/sounds", GOLD_SOUNDS), ("/images", GOLD_IMAGES)]:
            log(f"Cleaning {dir_path}...")
            fw.change_directory(dir_path, processor=FreeWiliProcessorType.Display)
            res = fw.list_current_directory(processor=FreeWiliProcessorType.Display).expect("List failed")
            
            for item in res.contents:
                f = item.name
                if f not in gold_list:
                    log(f"  Removing stale file: {dir_path}/{f}")
                    fw.remove_directory_or_file(f, processor=FreeWiliProcessorType.Display)
                else:
                    log(f"  Preserving: {f}")
        
        # 2. Re-upload latest assets to be sure
        log("Refreshing Gold Master assets...")
        asset_dir = "/home/ld/Pictures/Hackathon/src/assets/sfx"
        for sfx in GOLD_SOUNDS:
            local = os.path.join(asset_dir, sfx.replace("sfx_", ""))
            # Wait, the local filenames don't have sfx_ prefix usually
            if not os.path.exists(local):
                 # Try directly
                 local = os.path.join("/home/ld/Pictures/Hackathon/src/assets/sfx", sfx)
            
            if os.path.exists(local):
                log(f"  Uploading {sfx}...")
                fw.send_file(local, f"/sounds/{sfx}", processor=FreeWiliProcessorType.Display)
        
        log("Cleanup & Installation Complete.")
        fw.close()
    except Exception as e:
        log(f"FATAL: {e}")

if __name__ == "__main__":
    main()
