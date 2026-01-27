from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, Text

from extensions import BaseModel


class TournamentKnockoutConfigModel(BaseModel):
    __tablename__ = "tournament_knockout_config"

    id = Column(BigInteger, primary_key=True, index=True)
    tournamentId = Column(BigInteger, ForeignKey("tournaments.id"), nullable=False, name="tournament_id", unique=True)
    qualifiersPerGroup = Column(Integer, nullable=True, name="qualifiers_per_group")
    pairingMode = Column(String, nullable=True, name="pairing_mode")
    manualPairs = Column(Text, nullable=True, name="manual_pairs")
    pairingConfig = Column(Text, nullable=True, name="pairing_config")
    manualPairsByPhase = Column(Text, nullable=True, name="manual_pairs_by_phase")
