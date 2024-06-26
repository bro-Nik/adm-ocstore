"""movement.contact_id

Revision ID: 8f99bd359a76
Revises: 532d1527b1dc
Create Date: 2024-04-24 18:41:35.180669

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8f99bd359a76'
down_revision = '532d1527b1dc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('adm_stock_movement', schema=None) as batch_op:
        batch_op.create_foreign_key(None, 'adm_contact', ['contact_id'], ['contact_id'])
        # batch_op.drop_column('date')
        # batch_op.drop_column('name')

