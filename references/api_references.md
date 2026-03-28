# API & Software References

## Gemini API (Google)

Used for AI agent reasoning, structured game actions, and facial expression analysis from camera feed.

| Resource | Link |
|----------|------|
| **Google AI Studio** | https://aistudio.google.com |
| **Gemini API docs** | https://ai.google.dev/gemini-api/docs |
| **Structured output (JSON mode)** | https://ai.google.dev/gemini-api/docs/structured-output |
| **Vision / multimodal** | https://ai.google.dev/gemini-api/docs/vision |
| **Python SDK** | `pip install google-generativeai` |

### Usage in This Project
- **Game logic**: Agents reason about game state, produce structured JSON (role, action, public statement, private thoughts)
- **Facial analysis**: Camera feed frames sent to Gemini Vision to interpret human player reactions
- **Expression generation**: Internal agent state → emoji/SVG face for display

---

## ElevenLabs API

Used for text-to-speech (MVP) and real-time conversational AI (stretch goal).

| Resource | Link |
|----------|------|
| **ElevenLabs docs** | https://elevenlabs.io/docs |
| **TTS API** | https://elevenlabs.io/docs/api-reference/text-to-speech |
| **Conversational AI (ElevenAgents)** | https://elevenlabs.io/docs/conversational-ai |
| **Voice library** | https://elevenlabs.io/voice-library |
| **Python SDK** | `pip install elevenlabs` |

### Usage in This Project
- **MVP (TTS mode)**: Gemini generates agent dialogue → ElevenLabs converts to speech → piped to FREE-WILi speaker
- **Stretch (Live voice)**: ElevenAgents for real-time conversational interaction with human players

---

## FREE-WILi Python Library

Used to control the FREE-WILi hardware from the host laptop.

| Resource | Link |
|----------|------|
| **Python API docs** | https://freewili.github.io/freewili-python/ |
| **Install** | `pip install freewili` |

### Capabilities
- Control display (320×240 screen writes)
- Read button presses
- Control LEDs (patterns, colors)
- Play audio on speaker
- Capture microphone input
- Send/receive IR signals
- Control Sub-GHz radios (for wristband signaling)

---

## FREE-WILi WASM SDK

For on-device scripting (hardware I/O layer).

| Resource | Link |
|----------|------|
| **WASM examples** | https://github.com/freewili/wasm-examples |
| **fwwasm SDK** | https://github.com/freewili/fwwasm |
| **Supported languages** | C/C++, Rust, Zig, TinyGo |
