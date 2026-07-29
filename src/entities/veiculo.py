from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# Os portes que aparecem na base histórica. O check-in oferece esta lista, mas o
# campo é texto livre no banco — se aparecer um porte novo, não quebra nada.
TIPOS_CARRO = ("Hatch", "Sedã", "SUV", "Picape", "Utilitário")


class Veiculo(BaseModel):
    """O carro. Um cliente pode ter vários; a placa é o que os distingue."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    cliente_id: Optional[int] = None
    placa: Optional[str] = None
    tipo: Optional[str] = None
    modelo: Optional[str] = None
    criado_em: Optional[datetime] = None
