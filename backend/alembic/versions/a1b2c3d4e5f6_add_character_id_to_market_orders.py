"""add character_id to market_orders

Revision ID: a1b2c3d4e5f6
Revises: 3e51be4d9067
Create Date: 2024-11-14 20:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '3e51be4d9067'
branch_labels = None
depends_on = None


def upgrade():
    # Add character_id column to market_orders table
    op.add_column('market_orders', sa.Column('character_id', sa.BigInteger(), nullable=True))
    op.create_index('idx_market_orders_character', 'market_orders', ['character_id', 'is_active'])


def downgrade():
    # Remove index and column
    op.drop_index('idx_market_orders_character', table_name='market_orders')
    op.drop_column('market_orders', 'character_id')

