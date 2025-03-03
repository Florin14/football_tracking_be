from sqlalchemy import Column, Integer, ForeignKey, String, LargeBinary

from modules.user.models.user_model import UserModel


class PlayerModel(UserModel):
    __tablename__ = "players"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    position = Column(String, nullable=False)
    rating = Column(Integer, nullable=True)
    avatar = Column(LargeBinary, nullable=True)

    __mapper_args__ = {
        "polymorphic_identity": PlatformRoles.EMPLOYER,
        "inherit_condition": (id == UserModel.id),
    }
