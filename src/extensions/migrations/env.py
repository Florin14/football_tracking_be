from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import alembic_postgresql_enum
import os

# Get database URL from environment variable
def get_database_url():
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        return db_url
    raise RuntimeError("DATABASE_URL env var is required.")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Ensure the URL comes from env vars instead of the placeholder in alembic.ini.
config.set_main_option("sqlalchemy.url", get_database_url())

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
try:
    from extensions import BaseModel
    target_metadata = BaseModel.metadata
except ImportError:
    target_metadata = None


def _load_models() -> None:
    # Local imports to register all SQLAlchemy models without pulling routes.
    try:
        from modules.user import models as user_models  # noqa: F401
        from modules.admin import models as admin_models  # noqa: F401
        from modules.team import models as team_models  # noqa: F401
        from modules.player import models as player_models  # noqa: F401
        from modules.match import models as match_models  # noqa: F401
        from modules.tournament import models as tournament_models  # noqa: F401
        from modules.ranking import models as ranking_models  # noqa: F401
        from modules.notifications import models as notifications_models  # noqa: F401
        from modules.training import models as training_models  # noqa: F401
        from modules.attendance import models as attendance_models  # noqa: F401
        from modules.auth import models as auth_models  # noqa: F401
    except ImportError as e:
        import warnings
        warnings.warn(f"Could not import all models: {e}")
    except ImportError as e:
        # Handle import errors gracefully for migrations
        print(f"Warning: Could not import all models: {e}")
        pass

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
    _load_models()
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
    _load_models()
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
