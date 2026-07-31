from entities.importacao import Importacao
from repositories.importacao_repository import ImportacaoRepository


class ListImportacoesUseCase:
    """O histórico de cargas, da mais recente para a mais antiga — é a tabela
    que a página de importação mostra ao dono."""

    def __init__(self, importacao_repository: ImportacaoRepository):
        self.importacao_repository = importacao_repository

    def execute(self, limite: int = 20) -> dict:
        importacoes = self.importacao_repository.listar(limite)
        return {
            "status": "success",
            "data": [Importacao.como_dict(importacao) for importacao in importacoes],
        }
