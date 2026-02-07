from sqlalchemy import Column, Integer, ForeignKey, LargeBinary, Enum, BigInteger, func, select, literal
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, column_property

from constants.platform_roles import PlatformRoles
from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from constants.player_positions import PlayerPositions
from modules.team.models.team_model import TeamModel
from modules.user.models.user_model import UserModel
from modules.match.models.goal_model import GoalModel
from modules.match.models.card_model import CardModel
from modules.attendance.models.attendance_model import AttendanceModel
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

    goalsCount = column_property(
        select(func.count(GoalModel.id))
        .where(GoalModel.playerId == id)
        .correlate_except(GoalModel)
        .scalar_subquery()
    )
    assistsCount = column_property(literal(0))
    yellowCardsCount = column_property(
        select(func.count(CardModel.id))
        .where(
            CardModel.playerId == id,
            CardModel.cardType == CardType.YELLOW,
        )
        .correlate_except(CardModel)
        .scalar_subquery()
    )
    redCardsCount = column_property(
        select(func.count(CardModel.id))
        .where(
            CardModel.playerId == id,
            CardModel.cardType == CardType.RED,
        )
        .correlate_except(CardModel)
        .scalar_subquery()
    )
    appearancesCount = column_property(
        select(func.count(AttendanceModel.id))
        .where(
            AttendanceModel.playerId == id,
            AttendanceModel.scope == AttendanceScope.MATCH,
            AttendanceModel.status == AttendanceStatus.PRESENT,
        )
        .correlate_except(AttendanceModel)
        .scalar_subquery()
    )

    @property
    def teamName(self):
        return self.team.name if self.team else None

    @property
    def goals(self):
        return int(self.goalsCount or 0)

    @property
    def assists(self):
        return int(self.assistsCount or 0)

    @property
    def yellowCards(self):
        return int(self.yellowCardsCount or 0)

    @property
    def redCards(self):
        return int(self.redCardsCount or 0)

    @hybrid_property
    def appearances(self):
        return int(self.appearancesCount or 0)


    __mapper_args__ = {
        "polymorphic_identity": PlatformRoles.PLAYER,
        "inherit_condition": (id == UserModel.id),
    }
