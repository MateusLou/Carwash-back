from pydantic import BaseModel, ConfigDict
from typing import Optional, Literal, get_args
from datetime import datetime

StatusImportacao = Literal["processando", "concluida", "erro"]

STATUS_IMPORTACAO: tuple[str, ...] = get_args(StatusImportacao)


class Importacao(BaseModel):
    """Uma carga de planilha, do ponto de vista do negócio.

    É um job com três estados: nasce 'processando' quando o upload chega,
    termina 'concluida' com os contadores preenchidos ou 'erro' com o motivo.
    `detalhes` carrega o resumo por aba (o arquivo oficial tem uma por ano) —
    é o que a tela de importação mostra ao dono.
    """

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    arquivo: str
    aba: Optional[str] = None
    status: StatusImportacao = "processando"
    linhas_lidas: int = 0
    linhas_inseridas: int = 0
    linhas_ignoradas: int = 0
    iniciada_em: Optional[datetime] = None
    concluida_em: Optional[datetime] = None
    erro: Optional[str] = None
    detalhes: Optional[dict] = None

    @classmethod
    def como_dict(cls, model) -> dict:
        """O JSON que a API devolve, com timestamps em isoformat."""
        return cls.model_validate(model).model_dump(mode="json")
