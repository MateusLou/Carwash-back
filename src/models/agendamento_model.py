from sqlalchemy import Column, Text, Date, Time, CheckConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from database.database import Base


class AgendamentoModel(Base):
    """Espelho da tabela public.agendamentos do Supabase.

    Esta tabela já existe e é escrita pelo bot do n8n — o schema aqui reproduz
    supabase/schema.sql coluna por coluna. Se divergir, o próximo
    `alembic revision --autogenerate` vai propor alterações numa tabela que está
    em uso. Ao mexer, mexa nos dois lados.
    """

    __tablename__ = "agendamentos"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    # dados do cliente
    nome_cliente = Column(Text, nullable=True)
    telefone = Column(Text, nullable=False)

    # dados do veículo
    placa = Column(Text, nullable=True)
    modelo_carro = Column(Text, nullable=True)

    # dados do serviço
    servico = Column(Text, nullable=False, server_default=text("'Lavagem completa'"))
    data_agendamento = Column(Date, nullable=False)
    horario = Column(Time, nullable=False)

    # controle
    status = Column(Text, nullable=False, server_default=text("'pendente'"))
    observacoes = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "status in ('pendente','confirmado','concluido','cancelado')",
            name="agendamentos_status_check",
        ),
        Index("idx_agendamentos_data_horario", "data_agendamento", "horario"),
        Index("idx_agendamentos_status", "status"),
        Index("idx_agendamentos_telefone", "telefone"),
    )

    def __repr__(self):
        return (
            f"<Agendamento(id={self.id}, telefone={self.telefone}, "
            f"data={self.data_agendamento}, horario={self.horario}, status={self.status})>"
        )
