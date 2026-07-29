from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import date, datetime


class Funcionario(BaseModel):
    """Quem lava e quem recebe.

    Não há campo de função porque a operação não separa: dos 47 lavadores e 49
    atendentes da base histórica, 47 são a mesma pessoa nos dois papéis. O case
    descreve isso — "todos fazem um pouco de tudo".
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    nome: str
    ativo: bool = True
    admitido_em: Optional[date] = None
    desligado_em: Optional[date] = None
    criado_em: Optional[datetime] = None
