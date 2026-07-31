from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

from entities.veiculo import Veiculo


class Cliente(BaseModel):
    """Quem traz o carro, do ponto de vista do negócio.

    `cpf` é a identidade — o check-in exige, e a base histórica traz em todas as
    linhas. `nome` e `telefone` continuam podendo faltar: o nome falta em 14% da
    base e o telefone não existe lá. É o telefone que liga este cliente ao
    `agendamentos` que o bot criou no WhatsApp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    cpf: Optional[str] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None
    criado_em: Optional[datetime] = None

    def identificavel(self) -> bool:
        """Sem nenhum dos três não dá para reencontrar este cliente depois."""
        return bool(self.cpf or self.nome or self.telefone)


class ClienteComVeiculos(Cliente):
    """O cliente como o check-in precisa dele: com os carros que já trouxe.

    É o que faz o atendente escolher entre os veículos em vez de redigitar a
    placa. Vem vazio para os clientes importados — a base histórica não tem
    placa, só o porte do carro, que fica na lavagem.
    """

    veiculos: list[Veiculo] = []
