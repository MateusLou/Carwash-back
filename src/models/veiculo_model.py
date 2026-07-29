from sqlalchemy import Column, BigInteger, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from database.database import Base


class VeiculoModel(Base):
    """O carro. Um cliente pode ter vários.

    Nasce vazia: a base histórica não tem placa, só `tipo_carro` — que por isso
    fica também na própria lavagem, senão as métricas por porte de veículo
    parariam de funcionar para os 20 anos importados. Daqui pra frente o
    check-in cria o veículo pela placa.
    """

    __tablename__ = "veiculos"
    __table_args__ = (
        Index(
            "uq_veiculos_placa",
            "placa",
            unique=True,
            postgresql_where=text("placa is not null"),
        ),
        {"schema": "operacao"},
    )

    id = Column(BigInteger, primary_key=True)
    cliente_id = Column(
        BigInteger, ForeignKey("operacao.clientes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    placa = Column(Text, nullable=True)
    tipo = Column(Text, nullable=True)
    modelo = Column(Text, nullable=True)
    criado_em = Column(TIMESTAMP(timezone=True), nullable=False, server_default=text("now()"))

    def __repr__(self):
        return f"<Veiculo(id={self.id}, placa={self.placa}, tipo={self.tipo})>"
