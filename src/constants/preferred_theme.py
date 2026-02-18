from enum import Enum


class PreferredTheme(Enum):
    LIGHT = "LIGHT"
    DARK = "DARK"

    def __str__(self):
        return self.value
