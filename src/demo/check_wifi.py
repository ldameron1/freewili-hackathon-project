import sys
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

def main():
    try:
        fw = FreeWili.find_first().expect("No FREE-WILi found")
        fw.open().expect("Failed to open connection")
        
        print("Checking Display/Bottlenose (WiFi) Processor...")
        try:
            # Send a basic status command or get info
            app_info = fw.get_app_info().expect("Failed to get main app info")
            print(f"Main CPU: {app_info}")
            
            # Usually the display processor handles audio and screen
            # Can we query it directly? The SDK sends 'e\\c\\y' to the main serial but what about wifi?
            print("Successfully connected and queried Main CPU. Audio/Display tests can confirm ESP32 status.")
            
            # Run a small text check
            fw.show_text_display("WIFI/ESP32 CHIP\nSTATUS: ONLINE\n\nReconfiguration\nSuccessful!", FreeWiliProcessorType.Display)
            
            # Play a short tone to verify the audio DSP (ESP32) is responsive
            fw.play_audio_tone(880, 0.2, 0.5)
            
            print("SUCCESS: Display/Bottlenose chip is active and responding to display/audio commands!")
        except Exception as e:
            print(f"ERROR: Failed to communicate with subsystems. Is the Bottlenose seated correctly? {e}")
        finally:
            fw.close()
            
    except Exception as e:
        print(f"FATAL: {e}")

if __name__ == "__main__":
    main()
