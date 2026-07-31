"""Status e detalhes na importação

Revision ID: f4a1c9e27b53
Revises: 63197fba7a09
Create Date: 2026-07-31

A importação deixa de ser só um registro pós-fato do CLI e vira um job que o
painel acompanha: `status` conta em que pé está (o front faz polling), e
`detalhes` guarda o resumo por aba do arquivo multi-aba — a coluna `aba`
singular fica nula nesses uploads.

O default 'concluida' existe pelas linhas históricas: toda carga registrada
até aqui já terminou. O UPDATE de 'Fiado/Mensal' alinha os check-ins da
plataforma ao canônico 'Fiado' que a padronização da importação adota — sem
ele, o primeiro fiado registrado no balcão viraria uma sexta fatia no
dashboard.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4a1c9e27b53'
down_revision: Union[str, None] = '63197fba7a09'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'importacoes',
        sa.Column('status', sa.Text(), nullable=False, server_default='concluida'),
        schema='operacao',
    )
    op.create_check_constraint(
        'importacoes_status_check',
        'importacoes',
        "status in ('processando', 'concluida', 'erro')",
        schema='operacao',
    )
    op.add_column(
        'importacoes',
        sa.Column('detalhes', postgresql.JSONB(), nullable=True),
        schema='operacao',
    )
    # Cargas antigas do CLI que falharam já registravam o erro em texto.
    op.execute("update operacao.importacoes set status = 'erro' where erro is not null")
    op.execute(
        "update operacao.lavagens set metodo_pagamento = 'Fiado' "
        "where metodo_pagamento = 'Fiado/Mensal' and origem <> 'importacao'"
    )


def downgrade() -> None:
    # O UPDATE de 'Fiado/Mensal' não é revertido: não há como saber quais
    # linhas tinham o valor antigo.
    op.drop_constraint('importacoes_status_check', 'importacoes', schema='operacao')
    op.drop_column('importacoes', 'detalhes', schema='operacao')
    op.drop_column('importacoes', 'status', schema='operacao')
