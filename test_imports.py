import sys
import os

print("Testing imports...")
try:
    import freewili
    print("freewili imported")
    import google.genai
    print("google.genai imported")
    import elevenlabs
    print("elevenlabs imported")
    import flask
    print("flask imported")
    import psutil
    print("psutil imported")
    import dotenv
    print("dotenv imported")
    import pydantic
    print("pydantic imported")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

print("All imports successful.")
