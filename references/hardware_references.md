# Hardware References

## FREE-WILi (Core Device)

| Spec | Detail |
|------|--------|
| **Processor** | Raspberry Pi RP2040 (dual ARM Cortex-M0+ @ 133MHz) |
| **FPGA** | ICE40UP5k front-end with 8MB SRAM |
| **Display** | 320×240 color LCD |
| **Buttons** | 5 user-configurable |
| **LEDs** | 7 full-color |
| **Audio** | Digital speaker + microphone |
| **IR** | Transmitter and receiver |
| **Storage** | 16MB × 2 on-board (22MB usable) |
| **Battery** | 1000mAh Li-Ion with charger |
| **Radio** | Black: 2× CC1101 Sub-GHz (300–928 MHz) |
| **Extras** | RTC, Accelerometer, USB hub (2 FS + 1 HS) |

### Links
- **Main site**: https://freewili.com
- **Documentation**: https://docs.freewili.com
- **GitHub (firmware)**: https://github.com/freewili/freewili-firmware
- **Python library**: https://freewili.github.io/freewili-python/
- **WASM examples**: https://github.com/freewili/wasm-examples
- **fwwasm SDK**: https://github.com/freewili/fwwasm
- **Discord**: https://discord.com/invite/XJRBUCX62z

---

## ESP32-P4-EYE (WILEYE Camera Orca)

| Spec | Detail |
|------|--------|
| **SoC** | ESP32-P4 (dual-core RISC-V @ 400MHz + LP core @ 40MHz) |
| **Memory** | Up to 32MB PSRAM |
| **Camera** | MIPI-CSI with ISP |
| **Display** | 1.54" LCD (240×240, SPI) |
| **Video** | H.264 encoder up to 1080p@30fps |
| **Audio** | Onboard digital microphone |
| **WiFi/BT** | Via integrated ESP32-C6-MINI-1U (WiFi 6, BLE 5, Zigbee, Thread) |
| **Storage** | MicroSD slot |
| **USB** | USB 2.0 OTG High-Speed + USB Debug |
| **Extras** | Rotary encoder, LED fill light, battery connector |

### Links
- **User guide**: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32p4/esp32-p4-eye/user_guide.html
- **ESP-IDF**: https://github.com/espressif/esp-idf
- **Espressif ESP32-P4**: https://www.espressif.com/en/products/socs/esp32-p4

---

## DEF CON Wristbands

- Concert-style LED wristbands, likely PixMob-type
- Controlled via **433MHz RF** (not IR) — compatible with FREE-WILi's CC1101 Sub-GHz radios
- Can be triggered from the FREE-WILi to change colors/patterns per player role
- Used for role assignment signaling (e.g., red = Mafia, blue = Town)

### Links
- **FREE-WILi radio docs**: https://docs.freewili.com/scripting/radios/

---

## Bottlenose WiFi Orca (Optional)

| Spec | Detail |
|------|--------|
| **SoC** | ESP32-C6 |
| **Connectivity** | WiFi, Bluetooth, USB-C, Qwiic |
| **Use** | Adds WiFi to FREE-WILi for network API calls |

### Links
- **Orca modules**: https://docs.freewili.com/scripting/ (see Orca section)
