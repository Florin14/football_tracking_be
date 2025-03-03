from enum import Enum

from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy.ext.hybrid import hybrid_property

from extensions import BaseModel
from project_helpers.functions.generate_password import hash_password


class UserRole(Enum):
    ADMIN = "ADMIN"
    PLAYER = "PLAYER"


class UserModel(BaseModel):
    __tablename__ = "users"

    unhashed_password = ""

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.ADMIN)

    __mapper_args__ = {"polymorphic_identity": "user", "polymorphic_on": "role"}

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def password(self, value):
        self.unhashed_password = value
        self._password = hash_password(value)

    def getClaims(self):
        return {
            "userId": self.id,
            "role": self.role.name,
            "userName": self.name,
        }
