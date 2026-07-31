from sqlalchemy import Column, BigInteger, Text, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class ClienteModel(Base):
    """Quem traz o carro. Tabela do schema `operacao` (a plataforma), não do
    `public` (o bot).

    `cpf` é a identidade: é a única coluna que a base histórica traz preenchida
    em todas as linhas, e é o que o check-in passou a exigir. Guardado só com os
    dígitos.

    `telefone` é a ponte com o mundo do WhatsApp: é por ele que uma lavagem
    registrada aqui encontra o `public.agendamentos` que o bot criou. Nasce nulo
    porque a base histórica não tem telefone — quem preenche é o check-in.
    """

    __tablename__ = "clientes"
    __table_args__ = (
        # Nulo permitido de propósito: a obrigatoriedade do CPF é regra da API,
        # não do banco. Único parcial, para que os cadastros sem CPF (os que o
        # bot criar pelo telefone) continuem cabendo.
        Index(
            "uq_clientes_cpf",
            "cpf",
            unique=True,
            postgresql_where=text("cpf is not null"),
        ),
        # Comum, não único: com o CPF fazendo o papel de identidade, dois
        # homônimos de CPF diferente têm de caber. Serve só para a busca.
        Index("ix_clientes_nome_normalizado", "nome_normalizado"),
        Index(
            "uq_clientes_telefone",
            "telefone",
            unique=True,
            postgresql_where=text("telefone is not null"),
        ),
        {"schema": "operacao"},
    )

    id = Column(BigInteger, primary_key=True)
    cpf = Column(Text, nullable=True)
    nome = Column(Text, nullable=True)
    nome_normalizado = Column(Text, nullable=True)
    telefone = Column(Text, nullable=True)
    observacoes = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    atualizado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    def __repr__(self):
        return f"<Cliente(id={self.id}, cpf={self.cpf}, nome={self.nome})>"
