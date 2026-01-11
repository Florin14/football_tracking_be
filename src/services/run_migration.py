import os
from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text
from alembic.util.exc import CommandError

from extensions import SqlBaseModel
from extensions.sqlalchemy import SessionLocal
from extensions.sqlalchemy.init import DATABASE_URL
from modules import TournamentModel, LeagueModel
from modules.team.models import TeamModel

BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "extensions" / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"
VERSIONS_DIR = MIGRATIONS_DIR / "versions"
target_metadata = SqlBaseModel.metadata
alembicConfig = Config(
    str(ALEMBIC_INI),
    cmd_opts=Namespace(autogenerate=True, ignore_unknown_revisions=True, x=None)
)


def create_default_team(db_session, league_id: int | None):
    """Create the default Nordic Lions team if it doesn't exist"""
    try:
        # Check if Nordic Lions team already exists
        existingTeam = db_session.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()

        if not existingTeam:
            if league_id is None:
                raise RuntimeError("Default league is required to create the default team.")
            # Create Nordic Lions team
            nordic_lions = TeamModel(
                name="Nordic Lions",
                description="The default team for the Nordic Lions football club",
                isDefault=True,  # Assuming you want to mark it as default
                leagueId=league_id,
            )
            db_session.add(nordic_lions)
            db_session.commit()
            print(f"Created default team: {nordic_lions.name} (ID: {nordic_lions.id})")
        else:
            print(f"Default team already exists: {existingTeam.name} (ID: {existingTeam.id})")

    except Exception as e:
        print(f"Error creating default team: {e}")
        db_session.rollback()


def create_default_tournament(db_session) -> int | None:
    """Create the default Nordic Lions tournament if it doesn't exist"""
    try:
        # Check if Nordic Lions team already exists
        existingTournament = db_session.query(TournamentModel).filter(TournamentModel.isDefault.is_(True)).first()
        allTimeTournament = None
        if not existingTournament:
            # Create Nordic Lions team
            allTimeTournament = TournamentModel(
                name="CAMPIONATUL FIRMELOR ATS",
                description="The default tournament of Nordic Lions football club",
                isDefault=True  # Assuming you want to mark it as default
            )
            db_session.add(allTimeTournament)
            db_session.flush()

            print(f"Created default tournament: {allTimeTournament.name} (ID: {allTimeTournament.id})")
        else:
            print(f"Default tournament already exists: {existingTournament.name} (ID: {existingTournament.id})")

        existingLeague = db_session.query(LeagueModel).filter(LeagueModel.isDefault.is_(True)).first()

        if not existingLeague:
            # Create Nordic Lions team
            allTimeLeague = LeagueModel(
                name="DIVIZIA B2",
                description="ATS Cluj Tournament 2025-2026",
                isDefault=True,  # Assuming you want to mark it as default
                tournamentId=allTimeTournament.id if allTimeTournament else existingTournament.id if existingTournament else None,
            )
            db_session.add(allTimeLeague)
            print(f"Created default league: {allTimeLeague.name} (ID: {allTimeLeague.id})")
            league_id = allTimeLeague.id
        else:
            print(f"Default league already exists: {existingLeague.name} (ID: {existingLeague.id})")
            league_id = existingLeague.id

        db_session.commit()
        return league_id
    except Exception as e:
        print(f"Error creating default tournament or league: {e}")
        db_session.rollback()
        return None


session = SessionLocal()
session.execute(text("DROP TABLE IF EXISTS alembic_version;"))

session.commit()
alembicConfig.set_main_option("sqlalchemy.url",
                              DATABASE_URL)
alembicConfig.set_main_option("script_location", str(MIGRATIONS_DIR))
isExist = VERSIONS_DIR.exists()
if not isExist:
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
command.stamp(alembicConfig, revision="head")
command.revision(alembicConfig, autogenerate=True)
try:
    command.upgrade(alembicConfig, revision="head")
except CommandError as exc:
    message = str(exc)
    if "Can't locate revision identified by" in message:
        session.execute(text("DELETE FROM alembic_version;"))
        session.commit()
        command.stamp(alembicConfig, revision="head")
        command.upgrade(alembicConfig, revision="head")
    else:
        raise
command.stamp(alembicConfig, revision="head")
league_id = create_default_tournament(session)
create_default_team(session, league_id)

session.close()
exit(0)

