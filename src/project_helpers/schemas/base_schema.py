
from datetime import datetime, date
from enum import Enum
from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Enum: lambda v: str(v),
            datetime: lambda dt: dt.strftime("%Y-%m-%d %H:%M:%S"),
            date: lambda dt: dt.strftime("%Y-%m-%d"),
            type(None): lambda _: None
        },
    )
