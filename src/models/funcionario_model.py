from sqlalchemy import Column, BigInteger, Text, Boolean, Date, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class FuncionarioModel(Base):
    """Quem lava e quem recebe.

    Uma tabela só, sem coluna de função exclusiva: na base histórica há 47
    lavadores e 49 atendentes, com 47 nomes em comum — a mesma pessoa lava o
    carro e passa o cartão. Separar em duas tabelas duplicaria quase todo mundo.
    """

    __tablename__ = "funcionarios"
    __table_args__ = (
        Index("uq_funcionarios_nome_normalizado", "nome_normalizado", unique=True),
        {"schema": "operacao"},
    )

    id = Column(BigInteger, primary_key=True)
    nome = Column(Text, nullable=False)
    nome_normalizado = Column(Text, nullable=False)
    ativo = Column(Boolean, nullable=False, server_default=text("true"))
    admitido_em = Column(Date, nullable=True)
    desligado_em = Column(Date, nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    def __repr__(self):
        return f"<Funcionario(id={self.id}, nome={self.nome}, ativo={self.ativo})>"
