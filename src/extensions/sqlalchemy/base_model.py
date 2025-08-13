from pydantic import BaseModel as PyDantiModel
from sqlalchemy.orm import declarative_base

BaseModel = declarative_base()


class SqlBaseModel(BaseModel):
    __abstract__ = True

    def update(
        self,
        model: PyDantiModel,
        exclude=None,
        exclude_none=True,
        exclude_unset=False,
    ):
        for field, value in model.model_dump(
            exclude=exclude, exclude_none=exclude_none, exclude_unset=exclude_unset
        ).items():
            setattr(self, field, value)
