from pydantic import BaseModel, ConfigDict
from typing import Optional


class ReenviarContratoDTO(BaseModel):
    """O telefone é opcional: sem ele, vai para o número do cadastro.

    Quando vem, é porque o atendente descobriu que o número estava errado — e
    aí o reenvio também conserta o cadastro, senão o aviso de "carro pronto"
    erraria o alvo de novo dali a uma hora.
    """

    model_config = ConfigDict(extra="forbid")

    telefone: Optional[str] = None
