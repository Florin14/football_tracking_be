import os
import sys
import time
from argparse import Namespace
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.util.exc import CommandError
from sqlalchemy import text

from extensions.sqlalchemy import SessionLocal

# dacă ai DATABASE_URL definit aici, îl folosim ca fallback
try:
    from extensions.sqlalchemy.init import DATABASE_URL as INIT_DATABASE_URL  # type: ignore
except Exception:
    INIT_DATABASE_URL = None  # fallback

from modules.tournament.models.tournament_model import TournamentModel
from modules.tournament.models.league_model import LeagueModel
from modules.team.models.team_model import TeamModel
from modules.tournament.models.league_team_model import LeagueTeamModel


BASE_DIR = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = BASE_DIR / "extensions" / "migrations"
ALEMBIC_INI = MIGRATIONS_DIR / "alembic.ini"


def get_database_url() -> str:
    """
    Prioritate:
    1) env DATABASE_URL (cel mai sigur în Docker)
    2) extensions.sqlalchemy.init.DATABASE_URL (dacă există)
    """
    db_url = os.getenv("DATABASE_URL") or INIT_DATABASE_URL
    if not db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Please define DATABASE_URL in your .env / environment."
        )
    return db_url


def wait_for_db(max_attempts: int = 30, sleep_seconds: float = 2.0) -> None:
    """
    Așteaptă până DB acceptă conexiuni.
    Folosim SessionLocal (deci aceeași configurație ca aplicația).
    """
    last_exc: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            session = SessionLocal()
            try:
                session.execute(text("SELECT 1"))
                session.commit()
            finally:
                session.close()

            print(f"[migrations] DB is ready (attempt {attempt}/{max_attempts}).")
            return
        except Exception as exc:
            last_exc = exc
            print(
                f"[migrations] DB not ready yet (attempt {attempt}/{max_attempts}): {exc}"
            )
            time.sleep(sleep_seconds)

    raise RuntimeError(
        f"Database is not ready after {max_attempts} attempts. Last error: {last_exc}"
    )


def create_default_team(db_session, league_id: int | None) -> None:
    existing_team = (
        db_session.query(TeamModel)
        .filter(TeamModel.isDefault.is_(True))
        .first()
    )

    if existing_team:
        print(f"[seed] Default team already exists: {existing_team.name} (ID: {existing_team.id})")
        return

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

    print(f"[seed] Created default team: {base_camp.name} (ID: {base_camp.id})")


def create_default_tournament(db_session) -> int | None:
    existing_tournament = (
        db_session.query(TournamentModel)
        .filter(TournamentModel.isDefault.is_(True))
        .first()
    )

    all_time_tournament = None
    if not existing_tournament:
        all_time_tournament = TournamentModel(
            name="CAMPIONATUL FIRMELOR ATS",
            description="The default tournament of Base Camp football club",
            isDefault=True,
        )
        db_session.add(all_time_tournament)
        db_session.flush()
        print(f"[seed] Created default tournament: {all_time_tournament.name} (ID: {all_time_tournament.id})")
    else:
        print(f"[seed] Default tournament already exists: {existing_tournament.name} (ID: {existing_tournament.id})")

    existing_league = (
        db_session.query(LeagueModel)
        .filter(LeagueModel.isDefault.is_(True))
        .first()
    )

    if not existing_league:
        tournament_id = (
            all_time_tournament.id
            if all_time_tournament
            else existing_tournament.id
            if existing_tournament
            else None
        )
        all_time_league = LeagueModel(
            name="DIVIZIA B1 2025-2026",
            description="ATS Cluj Tournament 2025-2026",
            isDefault=True,
            tournamentId=tournament_id,
        )
        db_session.add(all_time_league)
        db_session.flush()
        league_id = all_time_league.id
        print(f"[seed] Created default league: {all_time_league.name} (ID: {all_time_league.id})")
    else:
        league_id = existing_league.id
        print(f"[seed] Default league already exists: {existing_league.name} (ID: {existing_league.id})")

    db_session.commit()
    return league_id


def build_alembic_config() -> Config:
    alembic_config = Config(
        str(ALEMBIC_INI),
        cmd_opts=Namespace(
            autogenerate=False,
            ignore_unknown_revisions=True,
            x=None,
        ),
    )
    alembic_config.set_main_option("script_location", str(MIGRATIONS_DIR))

    # IMPORTANT în Docker: forțează URL-ul corect
    db_url = get_database_url()
    alembic_config.set_main_option("sqlalchemy.url", db_url)

    return alembic_config


def run_migrations() -> None:
    alembic_config = build_alembic_config()

    print("[migrations] Running alembic upgrade head...")
    try:
        command.upgrade(alembic_config, revision="head")
        print("[migrations] Alembic upgrade head done.")
    except CommandError as exc:
        message = str(exc)
        print(f"[migrations] Alembic error: {message}")

        # cazul tău: db are alembic_version cu o revizie pe care codul curent nu o mai știe
        if "Can't locate revision identified by" in message:
            print("[migrations] Unknown revision detected. Clearing alembic_version and stamping head...")
            session = SessionLocal()
            try:
                session.execute(text("DELETE FROM alembic_version;"))
                session.commit()
            finally:
                session.close()

            command.stamp(alembic_config, revision="head")
            command.upgrade(alembic_config, revision="head")
            print("[migrations] Recovered from unknown revision and upgraded to head.")
            return

        raise


def main() -> None:
    # 1) Așteaptă DB
    wait_for_db(max_attempts=30, sleep_seconds=2.0)

    # 2) Rulează migrări
    run_migrations()

    # 3) Seed default data
    session = SessionLocal()
    try:
        league_id = create_default_tournament(session)
        create_default_team(session, league_id)
    finally:
        session.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # ca să fie evident în logs și să oprească startul uvicorn (din cauza &&)
        print(f"[migrations] Fatal error: {e}", file=sys.stderr)
        raise
