from fastapi import Depends
from sqlalchemy.orm import Session

from extensions import get_db
from project_helpers.error import Error
from project_helpers.exceptions import ErrorException


class GetInstanceFromPath:
    def __init__(self, instanceModel):
        self.instanceModel = instanceModel

    def __call__(self, id: int | str = None, db: Session = Depends(get_db)):
        instance = None
        if id is not None:
            instance = db.query(self.instanceModel).get(id)
        if instance is None:
            raise ErrorException(error=Error.DB_MODEL_INSTANCE_DOES_NOT_EXISTS)
        return instance
