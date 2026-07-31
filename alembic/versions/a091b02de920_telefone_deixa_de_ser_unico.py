"""Telefone deixa de ser único

Revision ID: a091b02de920
Revises: a91f30c7d5b8
Create Date: 2026-07-30

O check-in de um CPF novo cujo telefone já pertencia a outro cadastro morria em
IntegrityError: o `get_or_create` — certo — não rouba o cadastro de quem tem
outro CPF, mas o INSERT do cliente novo esbarrava em `uq_clientes_telefone`.

A regra de negócio agora é a inversa: telefone repetido tem de caber. O mesmo
número atende um casal que divide o celular, ou um cliente novo que chega com o
número que um cadastro antigo registrou. A identidade é o CPF; o telefone é só
a ponte com o WhatsApp, e vira índice comum, de busca.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a091b02de920'
down_revision: Union[str, None] = 'a91f30c7d5b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index('uq_clientes_telefone', table_name='clientes', schema='operacao')
    op.create_index(
        'ix_clientes_telefone',
        'clientes',
        ['telefone'],
        unique=False,
        schema='operacao',
    )


def downgrade() -> None:
    op.drop_index('ix_clientes_telefone', table_name='clientes', schema='operacao')
    # Só volta a ser único se ninguém dividir número — se dividirem, o downgrade
    # falha aqui, e é o aviso correto: o dado deixou de caber no formato antigo.
    op.create_index(
        'uq_clientes_telefone',
        'clientes',
        ['telefone'],
        unique=True,
        schema='operacao',
        postgresql_where=sa.text('telefone is not null'),
    )
