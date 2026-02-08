from enum import Enum


class PreferredLanguage(Enum):
    RO = "RO"
    EN = "EN"

    def __str__(self):
        return self.value
