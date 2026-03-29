import sys
import os

# Add src to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("Testing src imports...")
try:
    from src.game.state import GameState
    print("GameState imported")
    from src.game.engine import MafiaEngine
    print("MafiaEngine imported")
    from src.moderator.app import create_app
    print("Flask app created")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

print("All src imports successful.")
