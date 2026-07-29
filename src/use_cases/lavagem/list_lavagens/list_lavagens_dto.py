from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import date


class ListLavagensDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    status: Optional[str] = None
    funcionario_id: Optional[int] = None
    tipo_carro: Optional[str] = None
    cliente_id: Optional[int] = None
    # Teto no limite: são 37 mil lavagens no banco, e uma listagem sem limite
    # travaria a tela.
    limite: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)
