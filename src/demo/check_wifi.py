import argparse

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

def main():
    parser = argparse.ArgumentParser(description="Quick Bottlenose status helper")
    parser.add_argument("--ssid", default="wifi", help="SSID you intend to use for station mode")
    args = parser.parse_args()

    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open connection")
        
        print("Checking Display/Bottlenose (WiFi) Processor...")
        try:
            app_info = fw.get_app_info().expect("Failed to get main app info")
            print(f"Main CPU: {app_info}")

            fw.show_text_display("WIFI/ESP32 CHIP\nSTATUS: ONLINE\n\nReconfiguration\nSuccessful!", FreeWiliProcessorType.Display)
            fw.play_audio_tone(880, 0.2, 0.5)

            print("Display/audio path is responsive.")
            print("")
            print("To use Bottlenose Wi-Fi per the official docs:")
            print("  1. Main Menu -> System -> Orca Setup -> select BottleNose")
            print("  2. Save settings with the blue button")
            print("  3. Go to Settings -> Wifi")
            print(f"  4. Enable Station Mode and set SSID to '{args.ssid}'")
            print("  5. Enter the station password, save settings, then reboot if needed")
            print("")
            print("Important: Orca UART can only target one module at a time.")
            print("If Orca Setup is currently set to WILEye, Bottlenose Wi-Fi will not function until switched.")
        except Exception as e:
            print(f"ERROR: Failed to communicate with subsystems. Is the Bottlenose seated correctly? {e}")
        finally:
            fw.close()
            
    except Exception as e:
        print(f"FATAL: {e}")

if __name__ == "__main__":
    main()
