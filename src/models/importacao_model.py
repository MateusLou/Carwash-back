from sqlalchemy import CheckConstraint, Column, BigInteger, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from database.database import Base


class ImportacaoModel(Base):
    """Registro de cada carga de planilha.

    Existe para duas perguntas que sempre aparecem depois: "de onde veio esta
    linha?" e "como desfaço a carga errada?". Cada lavagem guarda o
    `importacao_id`, então apagar uma carga inteira é um DELETE por esse campo.

    Também é o job que o painel acompanha: o upload responde na hora e a carga
    roda em background — `status` é o que o polling do front lê. Num arquivo
    multi-aba, `aba` fica nula e o resumo por aba mora em `detalhes`.
    """

    __tablename__ = "importacoes"
    __table_args__ = (
        CheckConstraint(
            "status in ('processando', 'concluida', 'erro')",
            name="importacoes_status_check",
        ),
        {"schema": "operacao"},
    )

    id = Column(BigInteger, primary_key=True)
    arquivo = Column(Text, nullable=False)
    aba = Column(Text, nullable=True)
    status = Column(Text, nullable=False, server_default=text("'concluida'"))
    linhas_lidas = Column(Integer, nullable=False, server_default=text("0"))
    linhas_inseridas = Column(Integer, nullable=False, server_default=text("0"))
    linhas_ignoradas = Column(Integer, nullable=False, server_default=text("0"))
    iniciada_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))
    concluida_em = Column(TIMESTAMP(timezone=True), nullable=True)
    erro = Column(Text, nullable=True)
    detalhes = Column(JSONB, nullable=True)

    def __repr__(self):
        return f"<Importacao(id={self.id}, arquivo={self.arquivo}, inseridas={self.linhas_inseridas})>"
