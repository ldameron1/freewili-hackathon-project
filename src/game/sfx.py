import wave
import struct
import math
import random
import os
import json

# Narrator lines for Cold Storage (common static lines)
CORE_LINES = {
    "night_1": "Night 1 falls on the town. Everyone, close your eyes.",
    "day_1": "Day 1 breaks. The town awakens. You may now discuss.",
    "vote_start": "Discussion time is over. It is time to vote.",
    "miracle": "A miracle! No one died in the night.",
    "game_start": "The game begins.",
    "town_win": "The game is over. The Town has won!",
    "mafia_win": "The game is over. The Mafia has won!"
}

def generate_wav(filename, duration, sample_rate, func):
    """Generic WAV generator using a synthesis function."""
    n_samples = int(duration * sample_rate)
    with wave.open(filename, 'w') as f:
        f.setnchannels(1)  # Mono
        f.setsampwidth(2)  # 16-bit
        f.setframerate(sample_rate)
        
        for i in range(n_samples):
            t = i / sample_rate
            sample = func(t, duration)
            # Clip and pack
            sample = max(-1, min(1, sample))
            value = int(sample * 32767)
            f.writeframesraw(struct.pack('<h', value))

def night_bell_func(t, d):
    # Ominous Gong: Mixed inharmonic sines
    env = math.exp(-3 * t/d)
    # Frequencies for a dark bell feel
    f1, f2, f3, f4 = 80, 123, 165, 210
    val = (
        0.5 * math.sin(2 * math.pi * f1 * t) +
        0.3 * math.sin(2 * math.pi * f2 * t) +
        0.15 * math.sin(2 * math.pi * f3 * t) +
        0.05 * math.sin(2 * math.pi * f4 * t)
    )
    return val * env

def gunshot_func(t, d):
    # Sharp noise burst with low-end thump
    if t > 0.15: return 0 # Very short
    env = math.exp(-25 * t)
    # High frequency noise
    noise = random.uniform(-1, 1) * 0.7
    # Low frequency thump (80Hz)
    thump = math.sin(2 * math.pi * 80 * t) * 0.3
    return (noise + thump) * env

def morning_bell_func(t, d):
    # Bright village bell
    env = math.exp(-4 * t/d)
    f1, f2 = 440, 880
    val = (
        0.6 * math.sin(2 * math.pi * f1 * t) +
        0.4 * math.sin(2 * math.pi * f2 * t)
    )
    return val * env

def bake_narrator_lines(client, output_dir, voice_id):
    """Call ElevenLabs API to pre-synthesize lines into the static assets pool."""
    print(f"Baking narrator lines to {output_dir} using voice {voice_id}...")
    
    for key, text in CORE_LINES.items():
        try:
            filename = os.path.join(output_dir, f"narrator_{key}.wav")
            if os.path.exists(filename):
                print(f" [Skip] {key} already exists")
                continue
                
            print(f" [Bake] '{text}'...")
            audio_gen = client.text_to_speech.convert(
                text=text,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="pcm_16000"
            )
            audio_bytes = b"".join(audio_gen)
            
            # --- APPLY 8KHZ CONVERSION & GAIN (Same as announcer.py) ---
            samples = list(struct.unpack(f"{len(audio_bytes)//2}h", audio_bytes))
            # Downsample (16k -> 8k) and apply hackathon-gain (1.8x)
            final_samples = [int(math.tanh((s / 32768.0) * 1.8) * 32767) for s in samples[::2]]
            
            # Padding (Anti-pop)
            pad = [0] * int(8000 * 0.15)
            final_samples = pad + final_samples + pad
            
            with wave.open(filename, "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(8000)
                f.writeframes(struct.pack(f"{len(final_samples)}h", *final_samples))
        except Exception as e:
            print(f" [Error] Failed to bake {key}: {e}")

def init_sfx_assets(output_dir="sfx"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Synthesizing synth SFX assets in {output_dir}...")
    generate_wav(os.path.join(output_dir, "night_bell.wav"), 3.0, 8000, night_bell_func)
    generate_wav(os.path.join(output_dir, "gunshot.wav"), 1.0, 8000, gunshot_func)
    generate_wav(os.path.join(output_dir, "morning_bell.wav"), 2.0, 8000, morning_bell_func)
    
    # Check for ElevenLabs to bake voice lines
    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if api_key:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=api_key)
        # Import static ID
        try:
            from game.state import ANNOUNCER_VOICE_ID
            bake_narrator_lines(client, output_dir, ANNOUNCER_VOICE_ID)
        except ImportError:
            # Fallback if PYTHONPATH isn't set perfectly
            bake_narrator_lines(client, output_dir, "nPczCjzI2devNBz1zQrb")
    
    print("Asset Preparation Complete.")

if __name__ == "__main__":
    init_sfx_assets()
