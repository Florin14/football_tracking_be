from sqlalchemy import Boolean, Column, Date, String, ForeignKey, BigInteger
from sqlalchemy.orm import relationship

from extensions import BaseModel


class TournamentModel(BaseModel):
    __tablename__ = "tournaments"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    isDefault = Column(Boolean, default=False, name="is_default")
    startDate = Column(Date, nullable=True, name="start_date")
    endDate = Column(Date, nullable=True, name="end_date")
