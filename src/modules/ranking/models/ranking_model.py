from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, BigInteger
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from extensions import BaseModel


class RankingModel(BaseModel):
    __tablename__ = "ranking"

    id = Column(BigInteger, primary_key=True, index=True)
    description = Column(String, nullable=True)
    gamesPlayed = Column(Integer, nullable=False, default=0, name="games_played")
    gamesWon = Column(Integer, nullable=False, default=0, name="games_won")
    gamesLost = Column(Integer, nullable=False, default=0, name="games_lost")
    gamesTied = Column(Integer, nullable=False, default=0, name="games_tied")
    goalsScored = Column(Integer, nullable=False, default=0, name="goals_scored")
    goalsConceded = Column(Integer, nullable=False, default=0, name="goals_conceded")
    points = Column(Integer, nullable=False, default=0, name="points")

    leagueId = Column(BigInteger, ForeignKey("leagues.id"))
    league = relationship("LeagueModel")
    teamId = Column(BigInteger, ForeignKey("teams.id"), name="team_id", nullable=False)
    team = relationship("TeamModel")

    @hybrid_property
    def form(self):
        return "WDLWL"
