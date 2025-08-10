from dataclasses import dataclass, field
from typing import Tuple, List, Literal, Set

from PIL import Image
from disnake import Member


@dataclass
class CardConfig:
    name: str
    description: str
    price: int
    quantity_range: Tuple
    image: Image.Image
    primary_color: int
    secondary_color: int
    embed_color: int


@dataclass
class NonLegalPrompts:
    success: List[str]
    failure: List[str]


@dataclass
class WorkPrompts:
    legal: List[str]
    non_legal: NonLegalPrompts


@dataclass
class CrystallizationState:
    bet: int
    multiplier: float
    loss_chance: float


@dataclass
class CandyGameState:
    bet: int
    pre_taken_candies: int
    player_taken_candies: int


@dataclass
class CoguardState:
    bet: int
    multiplier: float
    current_number: int
    win_streak: int


@dataclass
class SCP173GameState:
    host: Member
    bet: int
    mode: Literal["normal", "last_man_standing"]
    players: Set[Member] = field(default_factory=set)
    message_id: int = 0
    channel_id: int = 0
    is_started: bool = False
