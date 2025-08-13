from typing import Literal, List, Optional
from .base_schema import BaseSchema


class ErrorSchema(BaseSchema):
    code: str = None
    message: str = None
    fields: Optional[List[str]] = []
    level: Literal["debug", "info", "warning", "error", "critical"] = "debug"

    def __str__(self):
        return f"[{self.code}] - {self.message}"

    def print(self):
        getattr(self, self.level)(str(self))
