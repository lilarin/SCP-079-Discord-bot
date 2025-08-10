from enum import Enum


class ItemType(str, Enum):
    CARD = "card"


class Color(Enum):
    LIGHT_PINK = 0xFFB9BC
    GREEN = 0x4CAF50
    RED = 0xE53935
    WHITE = 0xFFFFFF
    BLUE = 0x3498DB
    ORANGE = 0xFF8C00
    BLACK = 0x1e1e1e
    YELLOW = 0xffdd53
