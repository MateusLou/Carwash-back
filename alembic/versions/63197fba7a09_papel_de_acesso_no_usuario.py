"""Papel de acesso no usuário

Revision ID: 63197fba7a09
Revises: a091b02de920
Create Date: 2026-07-31

Dois papéis, decididos pela senha digitada no balcão: 'dono' vê a plataforma
inteira, 'funcionario' opera tudo menos o painel de números. A coluna nasce
com default 'funcionario' de propósito — privilégio se concede um a um, não
se herda por omissão.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '63197fba7a09'
down_revision: Union[str, None] = 'a091b02de920'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('role', sa.String(length=20), nullable=False, server_default='funcionario'),
    )


def downgrade() -> None:
    op.drop_column('users', 'role')
