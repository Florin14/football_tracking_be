from sqlalchemy import Column, Integer, ForeignKey, LargeBinary, Enum, BigInteger, func, select
from sqlalchemy.orm import relationship, column_property

from constants.platform_roles import PlatformRoles
from constants.player_positions import PlayerPositions
from modules.team.models.team_model import TeamModel
from modules.user.models.user_model import UserModel
# from modules.match.models.goal_model import GoalModel
# from modules.match.models.card_model import CardModel
# from modules.attendance.models.attendance_model import AttendanceModel  # noqa: F401
# from modules.notifications.models.notifications_model import NotificationModel  # noqa: F401
from constants.card_type import CardType


class PlayerModel(UserModel):
    __tablename__ = "players"

    id = Column(BigInteger, ForeignKey("users.id"), primary_key=True)
    position = Column(Enum(PlayerPositions), nullable=False, default=PlayerPositions.DEFENDER)
    rating = Column(Integer, nullable=True)
    shirtNumber = Column("shirt_number", Integer, nullable=True)
    avatar = Column(LargeBinary, nullable=True)
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    team = relationship(TeamModel)
    notifications = relationship("NotificationModel", back_populates="player")
    attendance = relationship("AttendanceModel", back_populates="player")

    # goalsCount = column_property(
    #     select(func.count(GoalModel.id))
    #     .where(GoalModel.playerId == id)
    #     .correlate_except(GoalModel)
    #     .scalar_subquery()
    # )
    # assistsCount = column_property(
    #     select(func.count(GoalModel.id))
    #     .where(GoalModel.assistPlayerId == id)
    #     .correlate_except(GoalModel)
    #     .scalar_subquery()
    # )
    # yellowCardsCount = column_property(
    #     select(func.count(CardModel.id))
    #     .where(
    #         CardModel.playerId == id,
    #         CardModel.cardType == CardType.YELLOW,
    #     )
    #     .correlate_except(CardModel)
    #     .scalar_subquery()
    # )
    # redCardsCount = column_property(
    #     select(func.count(CardModel.id))
    #     .where(
    #         CardModel.playerId == id,
    #         CardModel.cardType == CardType.RED,
    #     )
    #     .correlate_except(CardModel)
    #     .scalar_subquery()
    # )


    __mapper_args__ = {
        "polymorphic_identity": PlatformRoles.PLAYER,
        "inherit_condition": (id == UserModel.id),
    }
