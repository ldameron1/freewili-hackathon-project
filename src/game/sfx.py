import wave
import struct
import math
import random
import os

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

def init_sfx_assets(output_dir="sfx"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"Synthesizing SFX assets in {output_dir}...")
    
    generate_wav(os.path.join(output_dir, "night_bell.wav"), 3.0, 8000, night_bell_func)
    generate_wav(os.path.join(output_dir, "gunshot.wav"), 1.0, 8000, gunshot_func)
    generate_wav(os.path.join(output_dir, "morning_bell.wav"), 2.0, 8000, morning_bell_func)
    
    print("SFX Synthesis Complete.")

if __name__ == "__main__":
    init_sfx_assets()
