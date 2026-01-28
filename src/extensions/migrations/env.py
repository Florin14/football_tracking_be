from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from modules.user.models.user_model import UserModel  # noqa: F401
from modules.admin.models.admin_model import AdminModel  # noqa: F401
from modules.team.models.team_model import TeamModel  # noqa: F401
from modules.player.models.player_model import PlayerModel  # noqa: F401
from modules.match.models.match_model import MatchModel  # noqa: F401
from modules.match.models.goal_model import GoalModel  # noqa: F401
from modules.match.models.card_model import CardModel  # noqa: F401
from modules.attendance.models.attendance_model import AttendanceModel  # noqa: F401
from modules.tournament.models.tournament_model import TournamentModel  # noqa: F401
from modules.tournament.models.league_model import LeagueModel  # noqa: F401
from modules.tournament.models.league_team_model import LeagueTeamModel  # noqa: F401
from modules.tournament.models.tournament_group_model import TournamentGroupModel  # noqa: F401
from modules.tournament.models.tournament_group_team_model import TournamentGroupTeamModel  # noqa: F401
from modules.tournament.models.tournament_group_match_model import TournamentGroupMatchModel  # noqa: F401
from modules.tournament.models.tournament_knockout_match_model import TournamentKnockoutMatchModel  # noqa: F401
from modules.tournament.models.tournament_knockout_config_model import TournamentKnockoutConfigModel  # noqa: F401
from modules.ranking.models.ranking_model import RankingModel  # noqa: F401
from modules.notifications.models.notification_model import NotificationModel  # noqa: F401
from modules.training.models.training_session_model import TrainingSessionModel  # noqa: F401
import alembic_postgresql_enum

from extensions.sqlalchemy.init import build_database_url
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure the URL comes from env vars instead of the placeholder in alembic.ini.
config.set_main_option("sqlalchemy.url", build_database_url())

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from extensions import BaseModel
target_metadata = BaseModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        ignore_unknown_revisions=True
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
