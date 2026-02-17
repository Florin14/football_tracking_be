from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime

from extensions import BaseModel


class GoalModel(BaseModel):
    __tablename__ = "goals"

    id = Column(BigInteger, primary_key=True, index=True)
    matchId = Column(BigInteger, ForeignKey("matches.id"), nullable=False)
    playerId = Column(BigInteger, ForeignKey("players.id", ondelete="SET NULL"), nullable=True)
    playerNameSnapshot = Column(String(50), nullable=True, name="player_name_snapshot")
    assistPlayerId = Column(BigInteger, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, name="assist_player_id")
    assistPlayerNameSnapshot = Column(String(50), nullable=True, name="assist_player_name_snapshot")
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    minute = Column(Integer, nullable=True)  # minute when the goal was scored
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    description = Column(String, nullable=True)  # optional description of the goal

    match = relationship("MatchModel", back_populates="goals")
    player = relationship("PlayerModel", foreign_keys=[playerId])
    assistPlayer = relationship("PlayerModel", foreign_keys=[assistPlayerId])
    team = relationship("TeamModel")

    @property
    def playerName(self):
        if self.player:
            return self.player.name
        if self.playerNameSnapshot:
            return self.playerNameSnapshot
        return "Unknown"

    @property
    def assistPlayerName(self):
        if self.assistPlayer:
            return self.assistPlayer.name
        if self.assistPlayerNameSnapshot:
            return self.assistPlayerNameSnapshot
        return None

    @property
    def teamName(self):
        return self.team.name if self.team else "Unknown"
