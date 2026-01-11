from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config

from extensions.sqlalchemy import SessionLocal
from modules import TournamentModel, LeagueModel
from modules.team.models import TeamModel

BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "extensions" / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"


def create_default_team(db_session):
    existing_team = db_session.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()

    if not existing_team:
        nordic_lions = TeamModel(
            name="Nordic Lions",
            description="The default team for the Nordic Lions football club",
            isDefault=True
        )
        db_session.add(nordic_lions)
        db_session.commit()
        print(f"Created default team: {nordic_lions.name} (ID: {nordic_lions.id})")
        return

    print(f"Default team already exists: {existing_team.name} (ID: {existing_team.id})")


def create_default_tournament(db_session):
    existing_tournament = db_session.query(TournamentModel).filter(TournamentModel.isDefault.is_(True)).first()
    all_time_tournament = None

    if not existing_tournament:
        all_time_tournament = TournamentModel(
            name="CAMPIONATUL FIRMELOR ATS",
            description="The default tournament of Nordic Lions football club",
            isDefault=True
        )
        db_session.add(all_time_tournament)
        db_session.flush()
        print(f"Created default tournament: {all_time_tournament.name} (ID: {all_time_tournament.id})")
    else:
        print(f"Default tournament already exists: {existing_tournament.name} (ID: {existing_tournament.id})")

    existing_league = db_session.query(LeagueModel).filter(LeagueModel.isDefault.is_(True)).first()

    if not existing_league:
        all_time_league = LeagueModel(
            name="DIVIZIA B2",
            description="ATS Cluj Tournament 2025-2026",
            isDefault=True,
            tournamentId=all_time_tournament.id if all_time_tournament else existing_tournament.id if existing_tournament else None,
        )
        db_session.add(all_time_league)
        print(f"Created default league: {all_time_league.name} (ID: {all_time_league.id})")
    else:
        print(f"Default league already exists: {existing_league.name} (ID: {existing_league.id})")

    db_session.commit()


def run_migrations():
    alembic_config = Config(
        str(ALEMBIC_INI),
        cmd_opts=Namespace(autogenerate=False, ignore_unknown_revisions=True, x=None)
    )
    alembic_config.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(alembic_config, revision="head")


def main():
    run_migrations()
    session = SessionLocal()
    try:
        create_default_team(session)
        create_default_tournament(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
