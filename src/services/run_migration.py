import os
from argparse import Namespace

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from extensions import SqlBaseModel
from extensions.sqlalchemy import SessionLocal
from modules.team.models import TeamModel

target_metadata = SqlBaseModel.metadata
alembicConfig = Config(
    "extensions/migrations/alembic.ini",
    cmd_opts=Namespace(autogenerate=True, ignore_unknown_revisions=True, x=None)
)


def create_default_team(db_session):
    """Create the default Nordic Lions team if it doesn't exist"""
    try:
        # Check if Nordic Lions team already exists
        existing_team = db_session.query(TeamModel).filter(TeamModel.isDefault.is_(True)).first()
        
        if not existing_team:
            # Create Nordic Lions team
            nordic_lions = TeamModel(
                name="Nordic Lions",
                description="The default team for the Nordic Lions football club",
                isDefault=True  # Assuming you want to mark it as default
            )
            db_session.add(nordic_lions)
            db_session.commit()
            print(f"Created default team: {nordic_lions.name} (ID: {nordic_lions.id})")
        else:
            print(f"Default team already exists: {existing_team.name} (ID: {existing_team.id})")
    
    except Exception as e:
        print(f"Error creating default team: {e}")
        db_session.rollback()


session = SessionLocal()
session.execute(text("DROP TABLE IF EXISTS alembic_version;"))

session.commit()
alembicConfig.set_main_option("sqlalchemy.url", "postgresql://postgres:1234@localhost:5432/football_tracking_be")
alembicConfig.set_main_option("script_location", "extensions/migrations")
isExist = os.path.exists("extensions/migrations/versions")
if not isExist:
    os.makedirs("extensions/migrations/versions")
command.stamp(alembicConfig, revision="head")
command.revision(alembicConfig, autogenerate=True)
command.upgrade(alembicConfig, revision="head")
command.stamp(alembicConfig, revision="head")
create_default_team(session)
session.close()
exit(0)
