"""AI Agent — Gemini-powered Mafia player."""
from __future__ import annotations
import json
import os
import re
from typing import TYPE_CHECKING

import google.generativeai as genai
from google.generativeai import types as gtypes

if TYPE_CHECKING:
    from .state import GameState, Player, Role

# JSON schema for agent output
AGENT_SCHEMA = {
    "type": "object",
    "properties": {
        "private_thought": {
            "type": "string",
            "description": "Your internal reasoning — only you and the moderator can see this.",
        },
        "public_statement": {
            "type": "string",
            "description": "What you say out loud. Keep it under 3 sentences.",
        },
        "action": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["none", "vote", "accuse", "defend", "nominate", "kill", "save", "investigate"],
                },
                "target": {"type": "string", "description": "Name of the player targeted, or empty."},
            },
            "required": ["type", "target"],
        },
        "emotion": {
            "type": "string",
            "enum": ["calm", "nervous", "suspicious", "confident", "grieving", "angry", "amused"],
        },
    },
    "required": ["private_thought", "public_statement", "action", "emotion"],
}


MAFIA_SYSTEM = """You are {name}, playing Mafia. You are a member of the MAFIA.
Your secret allies are: {allies}.
Your personality: {personality}
You MUST lie, deceive, and avoid suspicion. Never reveal you are Mafia.
You know your role, your allies, and all private information from your own actions.
Respond ONLY with valid JSON matching the schema."""

TOWN_SYSTEM = """You are {name}, playing Mafia. You are a {role}.
Your personality: {personality}
{role_instructions}
You do NOT know who the Mafia members are. Use logic and social observation.
Respond ONLY with valid JSON matching the schema."""

ROLE_INSTRUCTIONS = {
    "Doctor": "Each night you protect one player. You cannot protect the same person two nights in a row. You may protect yourself.",
    "Detective": "Each night you investigate one player and learn if they are Mafia (yes) or not (no). Use this info carefully — revealing it makes you a target.",
    "Townsperson": "You have no special night ability. Win by deducing and eliminating Mafia through discussion and voting.",
}


import time

class AIAgent:
    def __init__(self, player: "Player", mafia_allies: list[str] | None = None):
        self.player = player
        self.mafia_allies = mafia_allies or []
        self.history: list[dict] = []
        self.last_protected: str | None = None

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest",
            generation_config=genai.GenerationConfig(
                temperature=0.9,
                response_mime_type="application/json",
            ),
        )
        self._build_system_prompt()
        self.chat = self.model.start_chat(history=[])

    def _build_system_prompt(self) -> str:
        role = self.player.role
        if role.value == "Mafia":
            self._system = MAFIA_SYSTEM.format(
                name=self.player.name,
                allies=", ".join(self.mafia_allies) if self.mafia_allies else "none",
                personality=self.player.personality,
            )
        else:
            self._system = TOWN_SYSTEM.format(
                name=self.player.name,
                role=role.value,
                personality=self.player.personality,
                role_instructions=ROLE_INSTRUCTIONS.get(role.value, ""),
            )
        return self._system

    def _call(self, prompt: str) -> dict:
        """Send a prompt and parse the JSON response."""
        full_prompt = f"{self._system}\n\n{prompt}"
        try:
            time.sleep(4.5)  # Pace to 13 RPM to respect Free Tier quota
            response = self.model.generate_content(full_prompt)
            text = response.text.strip()
            # Strip markdown code fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            result = json.loads(text)
            # Validate required keys
            for key in ["private_thought", "public_statement", "action", "emotion"]:
                if key not in result:
                    result[key] = ""
            if "action" not in result or not isinstance(result["action"], dict):
                result["action"] = {"type": "none", "target": ""}
            return result
        except Exception as e:
            print(f"[AGENT:{self.player.name}] Error: {e}")
            return {
                "private_thought": f"Error: {e}",
                "public_statement": "I... need a moment to think.",
                "action": {"type": "none", "target": ""},
                "emotion": "calm",
            }

    def night_action(self, game_context: str) -> dict:
        """Called during night phase. Role-specific."""
        role = self.player.role
        if role.value == "Mafia":
            prompt = f"NIGHT PHASE. {game_context}\nChoose a player to KILL (action.type=kill, action.target=PlayerName)."
        elif role.value == "Doctor":
            current_protected = self.last_protected
            prompt = f"NIGHT PHASE. {game_context}\nChoose a player to SAVE (action.type=save, action.target=PlayerName). You cannot protect '{current_protected}' again."
        elif role.value == "Detective":
            prompt = f"NIGHT PHASE. {game_context}\nChoose a player to INVESTIGATE (action.type=investigate, action.target=PlayerName)."
        else:
            return {"private_thought": "It is night. I wait.", "public_statement": "", "action": {"type": "none", "target": ""}, "emotion": "calm"}

        result = self._call(prompt)
        if role.value == "Doctor" and result["action"].get("target"):
            self.last_protected = result["action"]["target"]
        return result

    def day_discussion(self, game_context: str, transcript: str = "") -> dict:
        """Called during day discussion. Speaks publicly."""
        human_speech = f"\nHuman players said: {transcript}" if transcript else ""
        prompt = f"DAY {game_context}{human_speech}\nSpeak your mind. You may accuse, defend, or share observations. (action.type=accuse/defend/none)"
        return self._call(prompt)

    def day_vote(self, game_context: str, nominees: list[str]) -> dict:
        """Vote for a player to eliminate."""
        prompt = f"VOTING PHASE. {game_context}\nNominees: {', '.join(nominees)}. Cast your vote (action.type=vote, action.target=one of the nominees)."
        return self._call(prompt)

    def react_to_event(self, event: str) -> dict:
        """React to a game event (death announcement, etc.)."""
        return self._call(f"EVENT: {event}\nBriefly react or stay silent.")
