from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TeamModel(BaseModel):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    match_id = Column(Integer, ForeignKey("matches.id"), nullable=False)
    players = relationship("Player", secondary="team_players", back_populates="teams")