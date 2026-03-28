import time
import sys
from freewili import FreeWili
fw = FreeWili.find_first().unwrap()
fw.open().unwrap()
try:
    print("Testing WilEye Camera...")
    # Dest 0 = SD / Dest 1 = Flash? Let's try Dest 0, but if we need it on host, can we get it?
    # Actually, we can just run wileye_take_picture
    res = fw.wileye_take_picture(0, "test_pic.jpg")
    print(f"Picture dest 0 result: {res}")
    res2 = fw.wileye_take_picture(1, "test_pic2.jpg")
    print(f"Picture dest 1 result: {res2}")
    
    time.sleep(2)
    
    print("Trying to fetch file...")
    try:
        fw.get_file("test_pic.jpg", "laptop_pic.jpg", lambda msg: print(msg))
    except Exception as e:
        print(f"Fetch dest 0 error: {e}")
    try:
        fw.get_file("test_pic2.jpg", "laptop_pic2.jpg", lambda msg: print(msg))
    except Exception as e:
        print(f"Fetch dest 1 error: {e}")

    print("Testing Radio/IR for Wristband...")
    # If the user says "radio controlled band":
    if hasattr(fw, 'select_radio'):
        fw.select_radio(1)
        res = fw.write_radio(b'\xFF\x00\xAA\x55'*10)
        print(f"Radio transmit result: {res}")
    
    # Try IR just in case they are IR wristbands
    if hasattr(fw, 'transmit_ir_raw'):
        # Usually wristboards use simple IR.
        res_ir = fw.transmit_ir_raw([500, 500, 500, 500])
        print(f"IR transmit result: {res_ir}")
    
except Exception as e:
    print("Error:", e)
finally:
    fw.close()
