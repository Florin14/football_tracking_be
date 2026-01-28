from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import text

from extensions.sqlalchemy import SessionLocal
from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.league_model import LeagueModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_team_model import LeagueTeamModel

BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "extensions" / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"


def create_default_team(db_session, league_id: int | None):
    existing_team = db_session.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()

    if not existing_team:
        if league_id is None:
            raise RuntimeError("Default league is required to create the default team.")
        base_camp = TeamModel(
            name="FC Base Camp",
            description="The default team for the Base Camp football club",
            isDefault=True,
        )
        db_session.add(base_camp)
        db_session.flush()
        db_session.add(LeagueTeamModel(leagueId=league_id, teamId=base_camp.id))
        db_session.commit()
        print(f"Created default team: {base_camp.name} (ID: {base_camp.id})")
        return

    print(f"Default team already exists: {existing_team.name} (ID: {existing_team.id})")


def create_default_tournament(db_session) -> int | None:
    existing_tournament = db_session.query(TournamentModel).filter(TournamentModel.isDefault.is_(True)).first()
    all_time_tournament = None

    if not existing_tournament:
        all_time_tournament = TournamentModel(
            name="CAMPIONATUL FIRMELOR ATS",
            description="The default tournament of Base Camp football club",
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
            name="DIVIZIA B1 2025-2026",
            description="ATS Cluj Tournament 2025-2026",
            isDefault=True,
            tournamentId=all_time_tournament.id if all_time_tournament else existing_tournament.id if existing_tournament else None,
        )
        db_session.add(all_time_league)
        db_session.flush()
        print(f"Created default league: {all_time_league.name} (ID: {all_time_league.id})")
        league_id = all_time_league.id
    else:
        print(f"Default league already exists: {existing_league.name} (ID: {existing_league.id})")
        league_id = existing_league.id

    db_session.commit()
    return league_id


def run_migrations():
    alembic_config = Config(
        str(ALEMBIC_INI),
        cmd_opts=Namespace(autogenerate=False, ignore_unknown_revisions=True, x=None)
    )
    alembic_config.set_main_option("script_location", str(MIGRATIONS_DIR))
    try:
        command.upgrade(alembic_config, revision="head")
    except CommandError as exc:
        message = str(exc)
        if "Can't locate revision identified by" in message:
            # Clear unknown revisions, then align with current head without touching schema/data.
            session = SessionLocal()
            try:
                session.execute(text("DELETE FROM alembic_version;"))
                session.commit()
            finally:
                session.close()
            command.stamp(alembic_config, revision="head")
            command.upgrade(alembic_config, revision="head")
            return
        raise


def main():
    run_migrations()
    session = SessionLocal()
    try:
        league_id = create_default_tournament(session)
        create_default_team(session, league_id)
    finally:
        session.close()


if __name__ == "__main__":
    main()
