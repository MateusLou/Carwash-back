from repositories.agendamento_repository import AgendamentoRepository
from repositories.lavagem_repository import LavagemRepository
from use_cases.agendamento.list_agendamentos.list_agendamentos_dto import ListAgendamentosDTO
from entities.agendamento import Agendamento, STATUS_VALIDOS
from fastapi import Response


class ListAgendamentosUseCase:
    agendamento_repository: AgendamentoRepository

    def __init__(
        self,
        agendamento_repository: AgendamentoRepository,
        lavagem_repository: LavagemRepository,
    ):
        self.agendamento_repository = agendamento_repository
        self.lavagem_repository = lavagem_repository

    def execute(self, list_agendamentos_dto: ListAgendamentosDTO, response: Response):
        if list_agendamentos_dto.status and list_agendamentos_dto.status not in STATUS_VALIDOS:
            response.status_code = 422
            return {
                "status": "error",
                "message": f"Status inválido. Use um destes: {', '.join(STATUS_VALIDOS)}",
            }

        if (
            list_agendamentos_dto.data_inicio
            and list_agendamentos_dto.data_fim
            and list_agendamentos_dto.data_inicio > list_agendamentos_dto.data_fim
        ):
            response.status_code = 422
            return {"status": "error", "message": "A data inicial é posterior à data final"}

        agendamentos = self.agendamento_repository.list_by_filtros(
            data_inicio=list_agendamentos_dto.data_inicio,
            data_fim=list_agendamentos_dto.data_fim,
            status=list_agendamentos_dto.status,
            servico=list_agendamentos_dto.servico,
        )

        # Quem já chegou: uma consulta para a lista inteira, não uma por linha.
        lavagens = self.lavagem_repository.mapa_por_agendamentos(
            [a.id for a in agendamentos]
        )

        # O que sai daqui é a entity, não o model: o front conversa com o
        # conceito de negócio, não com o formato do banco.
        return {
            "status": "success",
            "total": len(agendamentos),
            "data": [Agendamento.com_chegada(a, lavagens.get(a.id)) for a in agendamentos],
        }
