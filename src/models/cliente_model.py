from sqlalchemy import Column, BigInteger, Text, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class ClienteModel(Base):
    """Quem traz o carro. Tabela do schema `operacao` (a plataforma), não do
    `public` (o bot).

    `telefone` é a ponte com o mundo do WhatsApp: é por ele que uma lavagem
    registrada aqui encontra o `public.agendamentos` que o bot criou. Nasce nulo
    porque a base histórica não tem telefone — quem preenche é o check-in.
    """

    __tablename__ = "clientes"
    __table_args__ = (
        # Deduplicação na importação: a base só traz o NOME do cliente, então é
        # o nome sem acento e em minúscula que serve de chave até existir
        # telefone. Índice único parcial: várias linhas sem nome são permitidas.
        Index(
            "uq_clientes_nome_normalizado",
            "nome_normalizado",
            unique=True,
            postgresql_where=text("nome_normalizado is not null"),
        ),
        Index(
            "uq_clientes_telefone",
            "telefone",
            unique=True,
            postgresql_where=text("telefone is not null"),
        ),
        {"schema": "operacao"},
    )

    id = Column(BigInteger, primary_key=True)
    nome = Column(Text, nullable=True)
    nome_normalizado = Column(Text, nullable=True)
    telefone = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    atualizado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    def __repr__(self):
        return f"<Cliente(id={self.id}, nome={self.nome}, telefone={self.telefone})>"
