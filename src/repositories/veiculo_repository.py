from sqlalchemy.orm import Session
from repositories.base_repository import BaseRepository
from models.veiculo_model import VeiculoModel
from typing import Optional
import re


def normalizar_placa(placa: str) -> str:
    """Maiúsculas, sem hífen nem espaço — "abc-1d23" e "ABC1D23" são a mesma."""
    return re.sub(r"[^A-Za-z0-9]", "", placa).upper()


class VeiculoRepository(BaseRepository[VeiculoModel]):
    def __init__(self, session: Session):
        super().__init__(session, VeiculoModel)

    def get_by_placa(self, placa: str) -> VeiculoModel | None:
        return (
            self.session.query(self.model)
            .filter(self.model.placa == normalizar_placa(placa))
            .first()
        )

    def list_by_cliente(self, cliente_id: int) -> list[VeiculoModel]:
        return self.session.query(self.model).filter(self.model.cliente_id == cliente_id).all()

    def get_or_create(
        self,
        placa: Optional[str] = None,
        cliente_id: Optional[int] = None,
        tipo: Optional[str] = None,
        modelo: Optional[str] = None,
    ) -> VeiculoModel | None:
        """Sem placa não há veículo: é a única identidade que o carro tem.

        A lavagem guarda `tipo_carro` por conta própria, então um check-in sem
        placa continua rendendo métrica por porte de veículo — só não rende
        histórico daquele carro específico.
        """
        if not placa:
            return None

        veiculo = self.get_by_placa(placa)
        if veiculo is None:
            return self.add(
                VeiculoModel(
                    placa=normalizar_placa(placa),
                    cliente_id=cliente_id,
                    tipo=tipo,
                    modelo=modelo,
                )
            )

        mudou = False
        for campo, valor in (("cliente_id", cliente_id), ("tipo", tipo), ("modelo", modelo)):
            if valor and not getattr(veiculo, campo):
                setattr(veiculo, campo, valor)
                mudou = True
        if mudou:
            self.session.commit()
            self.session.refresh(veiculo)
        return veiculo
