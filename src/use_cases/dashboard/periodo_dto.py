from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal
from datetime import date

Granularidade = Literal["dia", "semana", "mes"]


class PeriodoDTO(BaseModel):
    """O filtro que os quatro endpoints de dashboard compartilham.

    Fica fora das pastas dos use cases porque é o mesmo contrato para todos —
    quatro cópias idênticas sairiam de sincronia no primeiro campo novo.
    O case pede filtro por semana e mês; `dia` entra porque é o que faz sentido
    quando o período selecionado é curto.
    """

    model_config = ConfigDict(extra="forbid")

    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    granularidade: Granularidade = "mes"

    def invalido(self) -> Optional[str]:
        if self.data_inicio and self.data_fim and self.data_inicio > self.data_fim:
            return "A data inicial é posterior à data final"
        return None
