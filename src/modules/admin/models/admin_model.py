from sqlalchemy import Column, ForeignKey, BigInteger

from constants.platform_roles import PlatformRoles
from project_helpers.functions.generate_password import hash_password
from modules.user.models.user_model import UserModel


class AdminModel(UserModel):
    __tablename__ = "admins"

    id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)

    __mapper_args__ = {
        "polymorphic_identity": PlatformRoles.ADMIN,
        "with_polymorphic": "*",
    }
