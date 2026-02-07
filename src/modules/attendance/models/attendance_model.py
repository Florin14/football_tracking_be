from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, BigInteger, UniqueConstraint
from sqlalchemy.orm import relationship

from constants.attendance_scope import AttendanceScope
from constants.attendance_status import AttendanceStatus
from extensions import BaseModel


class AttendanceModel(BaseModel):
    __tablename__ = "attendances"

    id = Column(BigInteger, primary_key=True, index=True)
    scope = Column(Enum(AttendanceScope), nullable=False, default=AttendanceScope.MATCH)
    matchId = Column(BigInteger, ForeignKey("matches.id"), nullable=True)
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=True)
    trainingSessionId = Column(BigInteger, ForeignKey("training_sessions.id"), nullable=True, name="training_session_id")
    playerId = Column(BigInteger, ForeignKey("players.id"), nullable=False)
    teamId = Column(BigInteger, ForeignKey("teams.id"), nullable=False)
    status = Column(Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.UNKNOWN)
    note = Column(String, nullable=True)
    recordedAt = Column(DateTime, nullable=False, default=datetime.utcnow, name="recorded_at")

    match = relationship("MatchModel", back_populates="attendance")
    tournament = relationship("TournamentModel")
    trainingSession = relationship("TrainingSessionModel", back_populates="attendance")
    player = relationship("PlayerModel", back_populates="attendance")
    team = relationship("TeamModel")

    # __table_args__ = (
    #     UniqueConstraint(matchId, playerId, name="uq_match_attendance_player"),
    #     UniqueConstraint(tournamentId, playerId, name="uq_tournament_attendance_player"),
    #     UniqueConstraint(trainingSessionId, playerId, name="uq_training_attendance_player"),
    # )

    @property
    def playerName(self):
        return self.player.name if self.player else "Unknown"

    @property
    def teamName(self):
        return self.team.name if self.team else "Unknown"

    @property
    def resolvedLeagueId(self):
        value = getattr(self, "_resolvedLeagueId", None)
        if value is not None:
            return value
        if self.match and self.match.leagueId:
            return self.match.leagueId
        return None

    @property
    def resolvedTournamentId(self):
        value = getattr(self, "_resolvedTournamentId", None)
        if value is not None:
            return value
        if self.tournamentId is not None:
            return self.tournamentId
        if self.match and self.match.league:
            return self.match.league.tournamentId
        return None
