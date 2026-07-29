from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class Cliente(BaseModel):
    """Quem traz o carro, do ponto de vista do negócio.

    `nome` e `telefone` são os dois nulos: a base histórica só tem nome (e falta
    em 14% das linhas), o check-in a partir de agora coleta telefone. É o
    telefone que liga este cliente ao `agendamentos` que o bot criou no WhatsApp.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    nome: Optional[str] = None
    telefone: Optional[str] = None
    observacoes: Optional[str] = None
    criado_em: Optional[datetime] = None

    def identificavel(self) -> bool:
        """Sem nome e sem telefone não dá para reencontrar este cliente depois."""
        return bool(self.nome or self.telefone)
