from freewili import FreeWili
import sys

def test_ports():
    ports = ["/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]
    for p in ports:
        print(f"Trying port {p}...")
        try:
            fw = FreeWili(main_port=p)
            fw.open().expect("Open fail")
            print(f"SUCCESS on {p}!")
            fw.show_text_display("MANUAL CONNECT SUCCESS", 1)
            fw.close()
            return p
        except Exception as e:
            print(f"Failed {p}: {e}")
    return None

if __name__ == "__main__":
    test_ports()
