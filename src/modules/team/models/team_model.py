from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TeamModel(BaseModel):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False)  # 0 for false, 1 for true
    # matchId = Column(Integer, ForeignKey("matches.id"), name="match_id", nullable=True)
    players = relationship("PlayerModel", back_populates="team")
