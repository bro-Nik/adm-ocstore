"""contact.role

Revision ID: 532d1527b1dc
Revises: 
Create Date: 2024-04-10 15:54:19.191492

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '532d1527b1dc'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('adm_contact', schema=None) as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=64), nullable=True))

