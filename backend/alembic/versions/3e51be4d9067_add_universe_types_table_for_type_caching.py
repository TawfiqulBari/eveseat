"""Add universe_types table for type caching

Revision ID: 3e51be4d9067
Revises: 
Create Date: 2025-11-14 18:39:49.254094

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3e51be4d9067'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create universe_types table for caching EVE Online type information
    op.create_table(
        'universe_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('type_id', sa.BigInteger(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_id', sa.BigInteger(), nullable=True),
        sa.Column('group_name', sa.String(length=255), nullable=True),
        sa.Column('category_id', sa.BigInteger(), nullable=True),
        sa.Column('category_name', sa.String(length=255), nullable=True),
        sa.Column('mass', sa.Float(), nullable=True),
        sa.Column('volume', sa.Float(), nullable=True),
        sa.Column('capacity', sa.Float(), nullable=True),
        sa.Column('portion_size', sa.Integer(), nullable=True),
        sa.Column('published', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('icon_id', sa.Integer(), nullable=True),
        sa.Column('icon_url', sa.String(length=500), nullable=True),
        sa.Column('type_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_universe_types_type_id'), 'universe_types', ['type_id'], unique=True)
    op.create_index(op.f('ix_universe_types_name'), 'universe_types', ['name'], unique=False)
    op.create_index(op.f('ix_universe_types_group_id'), 'universe_types', ['group_id'], unique=False)
    op.create_index(op.f('ix_universe_types_category_id'), 'universe_types', ['category_id'], unique=False)
    op.create_index('idx_universe_types_group', 'universe_types', ['group_id'], unique=False)
    op.create_index('idx_universe_types_category', 'universe_types', ['category_id'], unique=False)
    op.create_index('idx_universe_types_name', 'universe_types', ['name'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_universe_types_name', table_name='universe_types')
    op.drop_index('idx_universe_types_category', table_name='universe_types')
    op.drop_index('idx_universe_types_group', table_name='universe_types')
    op.drop_index(op.f('ix_universe_types_category_id'), table_name='universe_types')
    op.drop_index(op.f('ix_universe_types_group_id'), table_name='universe_types')
    op.drop_index(op.f('ix_universe_types_name'), table_name='universe_types')
    op.drop_index(op.f('ix_universe_types_type_id'), table_name='universe_types')
    op.drop_table('universe_types')

