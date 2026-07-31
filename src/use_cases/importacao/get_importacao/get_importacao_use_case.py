from fastapi import Response

from entities.importacao import Importacao
from repositories.importacao_repository import ImportacaoRepository


class GetImportacaoUseCase:
    """Uma importação pelo id — é o que o polling do front consulta até o
    status sair de 'processando'."""

    def __init__(self, importacao_repository: ImportacaoRepository):
        self.importacao_repository = importacao_repository

    def execute(self, importacao_id: int, response: Response) -> dict:
        importacao = self.importacao_repository.get_by_id(importacao_id)
        if importacao is None:
            response.status_code = 404
            return {"status": "error", "message": "Importação não encontrada"}
        return {"status": "success", "data": Importacao.como_dict(importacao)}
