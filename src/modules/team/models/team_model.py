from sqlalchemy import Boolean, Column, LargeBinary, String, BigInteger
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TeamModel(BaseModel):
    __tablename__ = "teams"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    logo = Column(LargeBinary, nullable=True)
    location = Column(String, nullable=True)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False)
    players = relationship("PlayerModel", back_populates="team")
    leagueTeams = relationship(
        "LeagueTeamModel",
        back_populates="team",
        cascade="all, delete-orphan",
    )
    leagues = relationship("LeagueModel", secondary="league_teams", viewonly=True)

    @property
    def playerCount(self):
        return len(self.players) if self.players else 0

    def _get_ranking(self):
        return getattr(self, "_ranking", None)

    @property
    def points(self):
        ranking = self._get_ranking()
        return ranking.points if ranking else 0

    @property
    def goalsFor(self):
        ranking = self._get_ranking()
        return ranking.goalsScored if ranking else 0

    @property
    def goalsAgainst(self):
        ranking = self._get_ranking()
        return ranking.goalsConceded if ranking else 0

    @property
    def wins(self):
        ranking = self._get_ranking()
        return ranking.gamesWon if ranking else 0

    @property
    def draws(self):
        ranking = self._get_ranking()
        return ranking.gamesTied if ranking else 0

    @property
    def losses(self):
        ranking = self._get_ranking()
        return ranking.gamesLost if ranking else 0


