from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, BigInteger
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from extensions import BaseModel


class RankingModel(BaseModel):
    __tablename__ = "ranking"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    gamesPlayed = Column(Integer, nullable=False, default=0, name="games_played")
    gamesWon = Column(Integer, nullable=False, default=0, name="games_won")
    gamesLost = Column(Integer, nullable=False, default=0, name="games_lost")
    gamesTied = Column(Integer, nullable=False, default=0, name="games_tied")
    goalsScored = Column(Integer, nullable=False, default=0, name="goals_scored")
    goalsConceded = Column(Integer, nullable=False, default=0, name="goals_conceded")
    points = Column(Integer, nullable=False, default=0, name="points")


    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id")
    tournament = relationship("TournamentModel")
    # teams = relationship("TeamModel", back_populates="tournament")
    teamId = Column(BigInteger, ForeignKey("teams.id"), name="team_id", nullable=False)
    team = relationship("TeamModel")

    @hybrid_property
    def form(self):
        """Calculate the team's form based on the last 5 games."""
        # This is a placeholder implementation. You should replace it with actual logic.
        return "WWLWL"
