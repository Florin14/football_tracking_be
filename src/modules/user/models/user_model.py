from sqlalchemy import Column, Integer, String, Enum, Boolean, BigInteger
from sqlalchemy.ext.hybrid import hybrid_property

from constants.platform_roles import PlatformRoles
from extensions import BaseModel
from project_helpers.functions.generate_password import hash_password


class UserModel(BaseModel):
    __tablename__ = "users"

    unhashed_password = ""

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(40), nullable=True)
    _password = Column(String(300), nullable=False)
    role = Column(Enum(PlatformRoles), nullable=False, default=PlatformRoles.ADMIN)
    isDeleted = Column(Boolean, nullable=False, default=False)
    hasDefaultPassword = Column(Boolean, nullable=False, default=True, name="has_default_password")
    isAvailable = Column(Boolean, default=True, server_default="True", name="is_available")

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
