"""Initial migration - create users table

Revision ID: b7c1a4f92d10
Revises:
Create Date: 2026-07-29

Cria APENAS a tabela users. As tabelas agendamentos e conversas já existem no
Supabase — foram criadas pelo supabase/schema.sql e são escritas pelo bot do
n8n. Elas estão declaradas em src/models/ só para o SQLAlchemy poder consultá-las
(e para o autogenerate ter com o que comparar); recriá-las aqui apagaria dados em
uso.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c1a4f92d10'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('reset_pwd_token', sa.String(length=255), nullable=True),
        sa.Column('reset_pwd_token_sent_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
