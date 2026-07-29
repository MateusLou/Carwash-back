"""Cria o schema operacao: clientes, veiculos, funcionarios, importacoes, lavagens

Revision ID: c3d8e2a15f47
Revises: b7c1a4f92d10
Create Date: 2026-07-29

O schema `operacao` é a plataforma; o `public` continua sendo do bot de WhatsApp
(agendamentos, conversas) e do login (users). Mesma conexão, mesmo banco — o que
permite cruzar o agendamento feito pelo WhatsApp com a lavagem executada.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3d8e2a15f47'
down_revision: Union[str, None] = 'b7c1a4f92d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("create schema if not exists operacao")

    # ------------------------------------------------------------------
    # clientes
    # ------------------------------------------------------------------
    op.create_table(
        'clientes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.Text(), nullable=True),
        sa.Column('nome_normalizado', sa.Text(), nullable=True),
        sa.Column('telefone', sa.Text(), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('criado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='operacao',
    )
    # Únicos PARCIAIS: a base histórica tem 14% das linhas sem nome de cliente e
    # nenhum telefone. Um único comum barraria a segunda linha nula.
    op.create_index('uq_clientes_nome_normalizado', 'clientes', ['nome_normalizado'],
                    unique=True, schema='operacao',
                    postgresql_where=sa.text('nome_normalizado is not null'))
    op.create_index('uq_clientes_telefone', 'clientes', ['telefone'],
                    unique=True, schema='operacao',
                    postgresql_where=sa.text('telefone is not null'))

    # ------------------------------------------------------------------
    # veiculos
    # ------------------------------------------------------------------
    op.create_table(
        'veiculos',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('cliente_id', sa.BigInteger(), nullable=True),
        sa.Column('placa', sa.Text(), nullable=True),
        sa.Column('tipo', sa.Text(), nullable=True),
        sa.Column('modelo', sa.Text(), nullable=True),
        sa.Column('criado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cliente_id'], ['operacao.clientes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='operacao',
    )
    op.create_index('ix_operacao_veiculos_cliente_id', 'veiculos', ['cliente_id'], schema='operacao')
    op.create_index('uq_veiculos_placa', 'veiculos', ['placa'], unique=True, schema='operacao',
                    postgresql_where=sa.text('placa is not null'))

    # ------------------------------------------------------------------
    # funcionarios
    # ------------------------------------------------------------------
    op.create_table(
        'funcionarios',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('nome', sa.Text(), nullable=False),
        sa.Column('nome_normalizado', sa.Text(), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('admitido_em', sa.Date(), nullable=True),
        sa.Column('desligado_em', sa.Date(), nullable=True),
        sa.Column('criado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='operacao',
    )
    op.create_index('uq_funcionarios_nome_normalizado', 'funcionarios', ['nome_normalizado'],
                    unique=True, schema='operacao')

    # ------------------------------------------------------------------
    # importacoes
    # ------------------------------------------------------------------
    op.create_table(
        'importacoes',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('arquivo', sa.Text(), nullable=False),
        sa.Column('aba', sa.Text(), nullable=True),
        sa.Column('linhas_lidas', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('linhas_inseridas', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('linhas_ignoradas', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('iniciada_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('concluida_em', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('erro', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='operacao',
    )

    # ------------------------------------------------------------------
    # lavagens — a tabela-fato
    # ------------------------------------------------------------------
    op.create_table(
        'lavagens',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('id_externo', sa.BigInteger(), nullable=True),
        sa.Column('origem', sa.Text(), server_default=sa.text("'plataforma'"), nullable=False),
        sa.Column('importacao_id', sa.BigInteger(), nullable=True),
        sa.Column('agendamento_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('cliente_id', sa.BigInteger(), nullable=True),
        sa.Column('veiculo_id', sa.BigInteger(), nullable=True),
        sa.Column('tipo_carro', sa.Text(), nullable=True),
        sa.Column('funcionario_lavagem_id', sa.BigInteger(), nullable=True),
        sa.Column('atendente_pagamento_id', sa.BigInteger(), nullable=True),

        sa.Column('data', sa.Date(), nullable=False),
        sa.Column('chegou_em', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('iniciou_lavagem_em', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('terminou_lavagem_em', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('saiu_em', postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('pago_em', postgresql.TIMESTAMP(timezone=True), nullable=True),

        sa.Column('tempo_espera_antes_lavagem_min', sa.Float(), nullable=True),
        sa.Column('tempo_lavagem_total_min', sa.Float(), nullable=True),
        sa.Column('tempo_pos_lavagem_ate_retirada_min', sa.Float(), nullable=True),
        sa.Column('tempo_ate_pagamento_min', sa.Float(), nullable=True),

        sa.Column('t_teto_vidros_min', sa.Float(), nullable=True),
        sa.Column('t_capo_parabrisa_min', sa.Float(), nullable=True),
        sa.Column('t_laterais_portas_min', sa.Float(), nullable=True),
        sa.Column('t_traseira_min', sa.Float(), nullable=True),
        sa.Column('t_rodas_pneus_min', sa.Float(), nullable=True),
        sa.Column('t_interior_min', sa.Float(), nullable=True),

        sa.Column('servico', sa.Text(), server_default=sa.text("'Lavagem completa'"), nullable=False),
        sa.Column('preco_reais', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('metodo_pagamento', sa.Text(), nullable=True),
        sa.Column('cnpj_receita', sa.Text(), nullable=True),

        sa.Column('nps_cliente', sa.SmallInteger(), nullable=True),
        sa.Column('nota_google', sa.Float(), nullable=True),

        sa.Column('shampoo_ml', sa.Float(), nullable=True),
        sa.Column('cera_ml', sa.Float(), nullable=True),
        sa.Column('pretinho_ml', sa.Float(), nullable=True),
        sa.Column('aromatizante_ml', sa.Float(), nullable=True),

        sa.Column('status', sa.Text(), server_default=sa.text("'aguardando'"), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('dados_extras', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('criado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('atualizado_em', postgresql.TIMESTAMP(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.CheckConstraint(
            "status in ('aguardando','em_lavagem','pronta','concluida','cancelada')",
            name='lavagens_status_check'),
        sa.CheckConstraint(
            "origem in ('importacao','plataforma','bot')",
            name='lavagens_origem_check'),
        sa.CheckConstraint(
            'nps_cliente is null or (nps_cliente between 0 and 10)',
            name='lavagens_nps_check'),
        sa.CheckConstraint(
            'nota_google is null or (nota_google between 1 and 5)',
            name='lavagens_nota_google_check'),
        sa.ForeignKeyConstraint(['importacao_id'], ['operacao.importacoes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cliente_id'], ['operacao.clientes.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['veiculo_id'], ['operacao.veiculos.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['funcionario_lavagem_id'], ['operacao.funcionarios.id'],
                                ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['atendente_pagamento_id'], ['operacao.funcionarios.id'],
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        schema='operacao',
    )
    op.create_index('ix_operacao_lavagens_importacao_id', 'lavagens', ['importacao_id'], schema='operacao')
    op.create_index('ix_operacao_lavagens_agendamento_id', 'lavagens', ['agendamento_id'], schema='operacao')
    op.create_index('ix_operacao_lavagens_cliente_id', 'lavagens', ['cliente_id'], schema='operacao')
    op.create_index('ix_operacao_lavagens_veiculo_id', 'lavagens', ['veiculo_id'], schema='operacao')
    op.create_index('uq_lavagens_id_externo', 'lavagens', ['id_externo'], unique=True, schema='operacao',
                    postgresql_where=sa.text('id_externo is not null'))
    op.create_index('idx_lavagens_data', 'lavagens', ['data'], schema='operacao')
    op.create_index('idx_lavagens_data_funcionario', 'lavagens',
                    ['data', 'funcionario_lavagem_id'], schema='operacao')
    op.create_index('idx_lavagens_status', 'lavagens', ['status'], schema='operacao')


def downgrade() -> None:
    op.drop_table('lavagens', schema='operacao')
    op.drop_table('importacoes', schema='operacao')
    op.drop_table('funcionarios', schema='operacao')
    op.drop_table('veiculos', schema='operacao')
    op.drop_table('clientes', schema='operacao')
    op.execute('drop schema if exists operacao')
