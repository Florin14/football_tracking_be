from sqlalchemy import Column, Integer, ForeignKey, String, LargeBinary, Enum
from sqlalchemy.orm import relationship

from constants.platform_roles import PlatformRoles
from constants.player_positions import PlayerPositions
from modules.team.models.team_model import TeamModel
from modules.user.models.user_model import UserModel


class PlayerModel(UserModel):
    __tablename__ = "players"

    id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    position = Column(Enum(PlayerPositions), nullable=False, default=PlayerPositions.DEFENDER)
    rating = Column(Integer, nullable=True)
    avatar = Column(LargeBinary, nullable=True)
    teamId = Column(Integer, ForeignKey("teams.id"))
    team = relationship(TeamModel)

    __mapper_args__ = {
        "polymorphic_identity": PlatformRoles.PLAYER,
        "inherit_condition": (id == UserModel.id),
    }
