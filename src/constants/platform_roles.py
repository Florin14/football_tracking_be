from enum import Enum


class PlatformRoles(Enum):
    ADMIN = "ADMIN"
    PLAYER = "PLAYER"

    def __gt__(self, other):
        try:
            return self.value > other.value
        except:
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.value < other.value
        except:
            return NotImplemented

    def __ge__(self, other):
        try:
            return self.value >= other.value
        except:
            return NotImplemented

    def __le__(self, other):
        try:
            return self.value <= other.value
        except:
            return NotImplemented

    def __eq__(self, other):
        return self.value == str(other)

    def __hash__(self):
        return hash(self.value)

    def __str__(self):
        return self.name

    def __repr__(self):
        return str(self)