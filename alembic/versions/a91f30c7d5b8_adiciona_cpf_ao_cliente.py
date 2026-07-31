"""Adiciona cpf ao cliente e tira a unicidade do nome

Revision ID: a91f30c7d5b8
Revises: c3d8e2a15f47
Create Date: 2026-07-30

O CPF passa a ser a identidade do cliente. Ele é a única coluna que a base
histórica traz preenchida em 100% das linhas (795 CPFs distintos contra 789
nomes, e o nome falta em 14% da base bruta), e o check-in passou a exigi-lo.

Duas consequências, e as duas estão aqui:

1. `cpf` nasce nullable com índice único parcial. A obrigatoriedade é regra da
   API, não do banco — um NOT NULL barraria os cadastros que o bot cria só com
   telefone e impediria o downgrade.
2. `uq_clientes_nome_normalizado` deixa de ser único. Ele existia porque o nome
   era a única chave possível; com o CPF no lugar, dois homônimos de CPF
   diferente precisam caber. Na prática isso já é bloqueante: deduplicar a base
   por CPF produz 7 clientes cujo nome imputado é "Não informado", e o índice
   único barraria o segundo.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a91f30c7d5b8'
down_revision: Union[str, None] = 'c3d8e2a15f47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'clientes',
        sa.Column('cpf', sa.Text(), nullable=True),
        schema='operacao',
    )
    op.create_index(
        'uq_clientes_cpf',
        'clientes',
        ['cpf'],
        unique=True,
        schema='operacao',
        postgresql_where=sa.text('cpf is not null'),
    )

    # nome: de chave única a mero índice de busca
    op.drop_index('uq_clientes_nome_normalizado', table_name='clientes', schema='operacao')
    op.create_index(
        'ix_clientes_nome_normalizado',
        'clientes',
        ['nome_normalizado'],
        unique=False,
        schema='operacao',
    )


def downgrade() -> None:
    op.drop_index('ix_clientes_nome_normalizado', table_name='clientes', schema='operacao')
    # Só volta a ser único se não houver homônimo — se houver, o downgrade falha
    # aqui, e é o aviso correto: o dado deixou de caber no formato antigo.
    op.create_index(
        'uq_clientes_nome_normalizado',
        'clientes',
        ['nome_normalizado'],
        unique=True,
        schema='operacao',
        postgresql_where=sa.text('nome_normalizado is not null'),
    )

    op.drop_index('uq_clientes_cpf', table_name='clientes', schema='operacao')
    op.drop_column('clientes', 'cpf', schema='operacao')
