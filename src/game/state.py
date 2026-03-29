"""Game state dataclasses and enums for Mafia."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time


class GamePhase(Enum):
    LOBBY = "lobby"
    REGISTRATION = "registration"
    NIGHT = "night"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTE = "day_vote"
    GAME_OVER = "game_over"


class Role(Enum):
    TOWN = "Townsperson"
    MAFIA = "Mafia"
    DOCTOR = "Doctor"
    DETECTIVE = "Detective"


# LED colors per role: (R, G, B)
ROLE_LED_COLORS = {
    Role.MAFIA:     (25, 0, 0),
    Role.DOCTOR:    (0, 25, 0),
    Role.DETECTIVE: (0, 0, 25),
    Role.TOWN:      (15, 15, 15),
}

# ElevenLabs voice IDs (well-known free voices)
DEFAULT_VOICES = [
    "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "AZnzlk1XvdvUeBnXmlld",  # Domi
    "EXAVITQu4vr4xnSDxMaL",  # Bella
    "ErXwobaYiN019PkySvjV",  # Antoni
    "MF3mGyEYCl7XYWbV9V6O",  # Elli
    "TxGEqnHWrfWFTfGW9XjX",  # Josh
    "VR6AewLTigWG4xSOukaG",  # Arnold
    "pNInz6obpgDQGcFmaJgB",  # Adam
    "yoZ06aMxZJJ28mfd3POQ",  # Sam
]
ANNOUNCER_VOICE_ID = "nPczCjzI2devNBz1zQrb"  # Brian — neutral, authoritative


@dataclass
class NightActions:
    mafia_target: Optional[str] = None
    doctor_save: Optional[str] = None
    detective_investigate: Optional[str] = None
    detective_result: Optional[bool] = None  # True = target is Mafia


@dataclass
class Player:
    name: str
    role: Role
    is_ai: bool
    alive: bool = True
    voice_id: str = ""
    personality: str = ""
    face_id: str = ""  # Filename of their reference photo
    voice_profile_id: str = ""  # ElevenLabs or Gemini speaker reference
    talk_count: int = 0  # Track number of times spoken

    @property
    def role_label(self) -> str:
        return self.role.value

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role.value,
            "is_ai": self.is_ai,
            "alive": self.alive,
            "talk_count": self.talk_count,
        }


@dataclass
class GameLogEntry:
    timestamp: float
    phase: str
    message: str
    public: bool = True  # False = moderator/debug only

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "phase": self.phase,
            "message": self.message,
            "public": self.public,
        }


@dataclass
class GameState:
    players: list[Player] = field(default_factory=list)
    phase: GamePhase = GamePhase.LOBBY
    turn: int = 0  # 0 = Night 0, 1 = Day 1, etc.
    game_log: list[GameLogEntry] = field(default_factory=list)
    night_actions: NightActions = field(default_factory=NightActions)
    votes: dict[str, str] = field(default_factory=dict)  # voter -> target
    winner: Optional[str] = None  # "Town" | "Mafia" | None

    def living_players(self) -> list[Player]:
        return [p for p in self.players if p.alive]

    def mafia_players(self) -> list[Player]:
        return [p for p in self.living_players() if p.role == Role.MAFIA]

    def town_players(self) -> list[Player]:
        return [p for p in self.living_players() if p.role != Role.MAFIA]

    def get_player(self, name: str) -> Optional[Player]:
        for p in self.players:
            if p.name.lower() == name.lower():
                return p
        return None

    def log(self, message: str, public: bool = True) -> None:
        entry = GameLogEntry(
            timestamp=time.time(),
            phase=self.phase.value,
            message=message,
            public=public,
        )
        self.game_log.append(entry)
        print(f"[LOG/{self.phase.value.upper()}] {message}")

    def check_win_condition(self) -> Optional[str]:
        living = self.living_players()
        mafia = [p for p in living if p.role == Role.MAFIA]
        town = [p for p in living if p.role != Role.MAFIA]
        if not mafia:
            return "Town"
        if len(mafia) >= len(town):
            return "Mafia"
        return None

    def to_dict(self) -> dict:
        return {
            "phase": self.phase.value,
            "turn": self.turn,
            "players": [p.to_dict() for p in self.players],
            "votes": self.votes,
            "winner": self.winner,
            "log_count": len(self.game_log),
        }
