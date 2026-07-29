from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class RegistrarPagamentoDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preco_reais: float = Field(ge=0)
    metodo_pagamento: Optional[str] = None
    cnpj_receita: Optional[str] = None
    atendente_pagamento_id: Optional[int] = None
    # O NPS é opcional porque o cliente pode não querer responder — e é assim
    # que 43% das linhas da base ficaram sem nota.
    nps_cliente: Optional[int] = Field(default=None, ge=0, le=10)
