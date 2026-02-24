"""Manage per-tenant PostgreSQL schemas.

create_tenant_schema() creates a new schema and copies all tables from ``public``,
so every tenant starts with the same database structure.

seed_tenant_defaults() populates a freshly-created schema with initial data
(admin user, default tournament, league, and team).
"""

import logging
import os

from sqlalchemy import text
from sqlalchemy.orm import Session

from extensions.sqlalchemy.base_model import BaseModel as _Base

# Tables that live only in *public* and must NOT be copied into tenant schemas.
_PUBLIC_ONLY_TABLES = frozenset({"tenants", "alembic_version"})


def create_tenant_schema(db: Session, schema_name: str) -> None:
    """Create a PostgreSQL schema for a tenant and replicate the public tables."""
    db.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    for table in _Base.metadata.sorted_tables:
        if table.name in _PUBLIC_ONLY_TABLES:
            continue

        cols = []
        for col in table.columns:
            col_type = col.type.compile(dialect=db.bind.dialect)
            nullable = "" if col.nullable else " NOT NULL"
            pk = " PRIMARY KEY" if col.primary_key else ""
            default = ""
            if col.primary_key and "int" in str(col_type).lower():
                col_type = "BIGSERIAL"
                default = ""
                pk = " PRIMARY KEY"
            cols.append(f'"{col.name}" {col_type}{nullable}{default}{pk}')

        cols_sql = ", ".join(cols)
        ddl = f'CREATE TABLE IF NOT EXISTS "{schema_name}"."{table.name}" ({cols_sql})'
        db.execute(text(ddl))

    logging.info("Created tenant schema: %s", schema_name)


def seed_tenant_defaults(
    db: Session,
    schema_name: str,
    tenant_name: str,
    admin_email: str | None = None,
    admin_password: str | None = None,
) -> None:
    """Populate a tenant schema with initial seed data.

    Creates: admin user, default tournament, default league, default team.
    Must be called AFTER create_tenant_schema().
    """
    from modules.auth.models.admin_model import AdminModel
    from modules.team.models.team_model import TeamModel
    from modules.tournament.models.tournament_model import TournamentModel
    from modules.tournament.models.league_model import LeagueModel
    from modules.tournament.models.league_team_model import LeagueTeamModel

    # Switch search_path to the new schema
    db.execute(text(f'SET search_path TO "{schema_name}", public'))

    # 1. Admin user
    email = admin_email or os.getenv("DEFAULT_ADMIN_EMAIL", "admin@fcbasecamp.ro")
    password = admin_password or os.getenv("DEFAULT_ADMIN_PASSWORD", "BasecampAdmin123!")
    existing_admin = db.query(AdminModel).first()
    if not existing_admin:
        admin = AdminModel(
            name="Administrator",
            email=email,
            password=password,
        )
        db.add(admin)
        db.flush()
        logging.info("Seeded admin user for schema %s", schema_name)

    # 2. Default tournament
    tournament = TournamentModel(
        name="ATS",
        description=f"All-time standings for {tenant_name}",
        isDefault=True,
    )
    db.add(tournament)
    db.flush()

    # 3. Default league
    league = LeagueModel(
        name="Liga principala",
        description=f"Default league for {tenant_name}",
        isDefault=True,
        relevanceOrder=1,
        tournamentId=tournament.id,
    )
    db.add(league)
    db.flush()

    # 4. Default team (the tenant's own team)
    team = TeamModel(
        name=tenant_name,
        description=f"Default team for {tenant_name}",
        isDefault=True,
    )
    db.add(team)
    db.flush()

    # Link team to league
    db.add(LeagueTeamModel(leagueId=league.id, teamId=team.id))
    db.flush()

    # Reset search_path
    db.execute(text('SET search_path TO public'))

    logging.info("Seeded defaults for tenant schema %s: admin=%s, team=%s", schema_name, email, tenant_name)
