from dataclasses import dataclass
from typing import Tuple, List

from PIL import Image


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
