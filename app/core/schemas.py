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
