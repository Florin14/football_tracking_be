"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade_trigger():
    conn = op.get_bind()

    # in case of no search
    pass


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

    # manual section
    upgrade_trigger()


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
