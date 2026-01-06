from datetime import datetime, timedelta
from sqlalchemy import Column, String, BigInteger, DateTime
from extensions import SqlBaseModel


class LoginAttemptModel(SqlBaseModel):
    __tablename__ = "login-attempt"
    email = Column(String(50), primary_key=True, nullable=False, unique=True)
    attempt = Column(BigInteger, nullable=False, default=3, server_default="3")
    exp = Column(DateTime, nullable=True, default=lambda: datetime.now() + timedelta(hours=24))
