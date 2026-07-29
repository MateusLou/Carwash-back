from sqlalchemy import Column, BigInteger, Integer, Text, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class ImportacaoModel(Base):
    """Registro de cada carga de planilha.

    Existe para duas perguntas que sempre aparecem depois: "de onde veio esta
    linha?" e "como desfaço a carga errada?". Cada lavagem guarda o
    `importacao_id`, então apagar uma carga inteira é um DELETE por esse campo.
    """

    __tablename__ = "importacoes"
    __table_args__ = {"schema": "operacao"}

    id = Column(BigInteger, primary_key=True)
    arquivo = Column(Text, nullable=False)
    aba = Column(Text, nullable=True)
    linhas_lidas = Column(Integer, nullable=False, server_default=text("0"))
    linhas_inseridas = Column(Integer, nullable=False, server_default=text("0"))
    linhas_ignoradas = Column(Integer, nullable=False, server_default=text("0"))
    iniciada_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    concluida_em = Column(TIMESTAMP(timezone=True), nullable=True)
    erro = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Importacao(id={self.id}, arquivo={self.arquivo}, inseridas={self.linhas_inseridas})>"
