import os
import time
from google import genai

with open(".env", "r") as f:
    env_lines = f.read().splitlines()
    env = {l.split("=")[0]: l.split("=")[1].strip() for l in env_lines if "=" in l}

gemini_key = env.get("GEMINI_API_KEY")
local_file = "final_captured_proof.wav"

# Verified list from client.models.list()
# We exclude the image/music/embedding ones
MODELS_TO_TRY = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash-lite",
    "models/gemini-flash-latest",
    "models/gemini-flash-lite-latest",
    "models/gemini-3.1-flash-lite-preview",
]

def prove():
    print(f"--- CANONICAL TRANSCRIPTION PROOF ---")
    if not os.path.exists(local_file):
        print(f"Error: {local_file} not found.")
        return

    client = genai.Client(api_key=gemini_key)
    print(f"Uploading {local_file}...")
    audio_file = client.files.upload(file=local_file)
    
    success = False
    for model_name in MODELS_TO_TRY:
        print(f"Trying: {model_name}...")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=["Transcribe this audio exactly.", audio_file]
            )
            print(f"\nSUCCESS with {model_name}! Result:\n{response.text}\n")
            success = True
            break
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "quota" in err_msg.lower():
                print(f"  Quota full. Blacklisting {model_name}...")
                continue
            else:
                print(f"  Error with {model_name}: {e}")
    
    if not success:
        print("CRITICAL: All compatible models are exhausted.")
        
    try:
        client.files.delete(name=audio_file.name)
    except: pass

if __name__ == "__main__":
    prove()
