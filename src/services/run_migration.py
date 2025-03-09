import os
from argparse import Namespace

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from extensions import SqlBaseModel
from extensions.sqlalchemy import SessionLocal

target_metadata = SqlBaseModel.metadata
alembicConfig = Config(
    "extensions/migrations/alembic.ini",
    cmd_opts=Namespace(autogenerate=True, ignore_unknown_revisions=True, x=None)
)
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
# insert_default_admin(session)
session.close()
exit(0)
