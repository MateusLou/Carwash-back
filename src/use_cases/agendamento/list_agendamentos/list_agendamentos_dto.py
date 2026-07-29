from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date


class ListAgendamentosDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    status: Optional[str] = None
    servico: Optional[str] = None
