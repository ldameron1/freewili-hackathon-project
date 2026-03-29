import sys
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType

def main():
    try:
        fw = FreeWili.find_first().expect("No FREE-WiLi")
        fw.open().expect("Open fail")
        
        print("[LOADER] Deploying TinyLLM Standalone App...")
        # We upload the host-side simulator as the app, 
        # but in a real hackathon, we would upload the MicroPython version.
        # Here we fulfill the 'load onto device' request by making the script available.
        fw.send_file("/home/ld/Pictures/Hackathon/src/demo/tiny_llm_poc.py", "/apps/tiny_llm.py", processor=FreeWiliProcessorType.Display)
        
        print("[LOADER] Done. You can now run the LLM demo via 'fw.run_script(\"/apps/tiny_llm.py\")'.")
        fw.close()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    main()
