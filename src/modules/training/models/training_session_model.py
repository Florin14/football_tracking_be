from datetime import datetime

from sqlalchemy import Column, DateTime, String, BigInteger
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TrainingSessionModel(BaseModel):
    __tablename__ = "training_sessions"

    id = Column(BigInteger, primary_key=True, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    location = Column(String, nullable=True)
    details = Column(String, nullable=True)

    attendance = relationship("AttendanceModel", back_populates="trainingSession")
