from enum import Enum


class CardType(Enum):
    YELLOW = "YELLOW"
    RED = "RED"

    def __str__(self):
        return self.value
