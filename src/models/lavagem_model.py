from sqlalchemy import (
    Column, BigInteger, SmallInteger, Text, Date, Float, Numeric,
    ForeignKey, CheckConstraint, Index, text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID, JSONB
from database.database import Base


class LavagemModel(Base):
    """A tabela-fato da plataforma: uma linha por carro lavado.

    Os nomes das colunas repetem os da planilha (`tempo_espera_antes_lavagem_min`,
    `preco_reais`, `cnpj_receita`…) de propósito: a importação vira um mapa 1:1 e
    quem comparar planilha com banco lê a mesma palavra nos dois lados.

    Quase tudo é nulo porque a base é assim — `nota_google` falta em 55% das
    linhas, `nps_cliente` em 43%, até `cliente` falta em 14%. Só 4,6% das linhas
    estão completas. Exigir NOT NULL aqui seria recusar a própria base.

    Sobre horário x duração: linha importada só tem duração (a planilha não
    registra relógio); linha registrada pela plataforma tem os carimbos, e o use
    case calcula a duração a partir deles. **A duração é sempre a fonte das
    métricas** — assim os 20 anos importados e a lavagem de hoje entram no mesmo
    gráfico.
    """

    __tablename__ = "lavagens"
    __table_args__ = (
        CheckConstraint(
            "status in ('aguardando','em_lavagem','pronta','concluida','cancelada')",
            name="lavagens_status_check",
        ),
        CheckConstraint(
            "origem in ('importacao','plataforma','bot')",
            name="lavagens_origem_check",
        ),
        CheckConstraint(
            "nps_cliente is null or (nps_cliente between 0 and 10)",
            name="lavagens_nps_check",
        ),
        CheckConstraint(
            "nota_google is null or (nota_google between 1 and 5)",
            name="lavagens_nota_google_check",
        ),
        Index("uq_lavagens_id_externo", "id_externo", unique=True,
              postgresql_where=text("id_externo is not null")),
        Index("idx_lavagens_data", "data"),
        Index("idx_lavagens_data_funcionario", "data", "funcionario_lavagem_id"),
        Index("idx_lavagens_status", "status"),
        {"schema": "operacao"},
    )

    # --- identidade -----------------------------------------------------
    id = Column(BigInteger, primary_key=True)
    # o id_lavagem da planilha; é o que torna a reimportação idempotente
    id_externo = Column(BigInteger, nullable=True)
    origem = Column(Text, nullable=False, server_default=text("'plataforma'"))
    importacao_id = Column(
        BigInteger, ForeignKey("operacao.importacoes.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    # Ligação fraca (sem FK) com public.agendamentos, do bot de WhatsApp:
    # aquele schema é de outro sistema, e uma FK faria o n8n esbarrar na nossa
    # tabela para apagar um agendamento dele.
    agendamento_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # --- quem -----------------------------------------------------------
    cliente_id = Column(
        BigInteger, ForeignKey("operacao.clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    veiculo_id = Column(
        BigInteger, ForeignKey("operacao.veiculos.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # desnormalizado: a base histórica tem tipo_carro mas não tem placa, então
    # sem esta coluna as métricas por porte de veículo perderiam 20 anos
    tipo_carro = Column(Text, nullable=True)
    funcionario_lavagem_id = Column(
        BigInteger, ForeignKey("operacao.funcionarios.id", ondelete="SET NULL"), nullable=True
    )
    atendente_pagamento_id = Column(
        BigInteger, ForeignKey("operacao.funcionarios.id", ondelete="SET NULL"), nullable=True
    )

    # --- quando ---------------------------------------------------------
    # `data` é o eixo de todos os filtros do dashboard
    data = Column(Date, nullable=False)
    chegou_em = Column(TIMESTAMP(timezone=True), nullable=True)
    iniciou_lavagem_em = Column(TIMESTAMP(timezone=True), nullable=True)
    terminou_lavagem_em = Column(TIMESTAMP(timezone=True), nullable=True)
    saiu_em = Column(TIMESTAMP(timezone=True), nullable=True)
    pago_em = Column(TIMESTAMP(timezone=True), nullable=True)

    # --- durações (fonte das métricas) ----------------------------------
    tempo_espera_antes_lavagem_min = Column(Float, nullable=True)
    tempo_lavagem_total_min = Column(Float, nullable=True)
    tempo_pos_lavagem_ate_retirada_min = Column(Float, nullable=True)
    tempo_ate_pagamento_min = Column(Float, nullable=True)

    # --- etapas da lavagem ----------------------------------------------
    t_teto_vidros_min = Column(Float, nullable=True)
    t_capo_parabrisa_min = Column(Float, nullable=True)
    t_laterais_portas_min = Column(Float, nullable=True)
    t_traseira_min = Column(Float, nullable=True)
    t_rodas_pneus_min = Column(Float, nullable=True)
    t_interior_min = Column(Float, nullable=True)

    # --- comercial ------------------------------------------------------
    servico = Column(Text, nullable=False, server_default=text("'Lavagem completa'"))
    preco_reais = Column(Numeric(10, 2), nullable=True)
    metodo_pagamento = Column(Text, nullable=True)
    # apesar do nome, a planilha guarda a razão social, não o número do CNPJ
    cnpj_receita = Column(Text, nullable=True)

    # --- satisfação -----------------------------------------------------
    nps_cliente = Column(SmallInteger, nullable=True)
    nota_google = Column(Float, nullable=True)

    # --- insumos --------------------------------------------------------
    shampoo_ml = Column(Float, nullable=True)
    cera_ml = Column(Float, nullable=True)
    pretinho_ml = Column(Float, nullable=True)
    aromatizante_ml = Column(Float, nullable=True)

    # --- controle -------------------------------------------------------
    status = Column(Text, nullable=False, server_default=text("'aguardando'"))
    observacoes = Column(Text, nullable=True)
    # Colchão para a base que ainda vai chegar: coluna nova que não tem casa cai
    # aqui sem migration. Quando se mostrar permanente, vira coluna de verdade.
    dados_extras = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    atualizado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    # As telas mostram nome de cliente e placa, não id. Estes relacionamentos
    # não mudam o DDL — são só o caminho para chegar lá sem escrever join à mão.
    # Quem lista muitas linhas usa joinedload, senão vira N+1.
    cliente = relationship("ClienteModel", lazy="select")
    veiculo = relationship("VeiculoModel", lazy="select")
    funcionario_lavagem = relationship(
        "FuncionarioModel", foreign_keys=[funcionario_lavagem_id], lazy="select"
    )
    atendente_pagamento = relationship(
        "FuncionarioModel", foreign_keys=[atendente_pagamento_id], lazy="select"
    )

    def __repr__(self):
        return (
            f"<Lavagem(id={self.id}, data={self.data}, status={self.status}, "
            f"preco={self.preco_reais})>"
        )
