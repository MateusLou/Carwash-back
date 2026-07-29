from repositories.lavagem_repository import LavagemRepository
from use_cases.lavagem.list_lavagens.list_lavagens_dto import ListLavagensDTO
from entities.lavagem import Lavagem, STATUS_VALIDOS
from fastapi import Response


class ListLavagensUseCase:
    """O histórico, com os mesmos filtros do dashboard."""

    def __init__(self, lavagem_repository: LavagemRepository):
        self.lavagem_repository = lavagem_repository

    def execute(self, list_dto: ListLavagensDTO, response: Response):
        if list_dto.status and list_dto.status not in STATUS_VALIDOS:
            response.status_code = 422
            return {
                "status": "error",
                "message": f"Status inválido. Use um destes: {', '.join(STATUS_VALIDOS)}",
            }

        if (
            list_dto.data_inicio
            and list_dto.data_fim
            and list_dto.data_inicio > list_dto.data_fim
        ):
            response.status_code = 422
            return {"status": "error", "message": "A data inicial é posterior à data final"}

        filtros = {
            "data_inicio": list_dto.data_inicio,
            "data_fim": list_dto.data_fim,
            "status": list_dto.status,
            "funcionario_id": list_dto.funcionario_id,
            "tipo_carro": list_dto.tipo_carro,
            "cliente_id": list_dto.cliente_id,
        }

        lavagens = self.lavagem_repository.list_by_filtros(
            limite=list_dto.limite, offset=list_dto.offset, **filtros
        )

        return {
            "status": "success",
            # o total é o do filtro inteiro, não o da página — é o que a tela
            # precisa para saber se há mais
            "total": self.lavagem_repository.contar(**filtros),
            "limite": list_dto.limite,
            "offset": list_dto.offset,
            "data": [Lavagem.com_nomes(m) for m in lavagens],
        }
