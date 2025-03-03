# Id: error_schema.py 202305 12/05/2023
#
# backend
# Copyright (c) 2011-2013 IntegraSoft S.R.L. All rights reserved.
#
# Author: cicada
#   Rev: 202305
#   Date: 12/05/2023
#
# License description...
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
