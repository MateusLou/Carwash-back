from repositories.agendamento_repository import AgendamentoRepository
from use_cases.agendamento.update_status_agendamento.update_status_agendamento_dto import (
    UpdateStatusAgendamentoDTO,
)
from entities.agendamento import Agendamento, TRANSICOES_PERMITIDAS
from fastapi import Response
from uuid import UUID


class UpdateStatusAgendamentoUseCase:
    """Confirmar, concluir ou cancelar um agendamento."""

    agendamento_repository: AgendamentoRepository

    def __init__(self, agendamento_repository: AgendamentoRepository):
        self.agendamento_repository = agendamento_repository

    def execute(
        self,
        agendamento_id: UUID,
        update_status_dto: UpdateStatusAgendamentoDTO,
        response: Response,
    ):
        agendamento_model = self.agendamento_repository.get_by_id(agendamento_id)

        if agendamento_model is None:
            response.status_code = 404
            return {"status": "error", "message": "Agendamento não encontrado"}

        agendamento = Agendamento.model_validate(agendamento_model)

        if agendamento.status == update_status_dto.novo_status:
            response.status_code = 409
            return {
                "status": "error",
                "message": f"O agendamento já está como '{agendamento.status}'",
            }

        # Quem sabe se a transição vale é a entity — a regra é de negócio.
        if not agendamento.pode_mudar_para(update_status_dto.novo_status):
            permitidos = TRANSICOES_PERMITIDAS.get(agendamento.status, ())
            response.status_code = 409
            return {
                "status": "error",
                "message": (
                    f"Não dá para ir de '{agendamento.status}' para "
                    f"'{update_status_dto.novo_status}'. "
                    + (
                        f"A partir de '{agendamento.status}', só: {', '.join(permitidos)}."
                        if permitidos
                        else f"'{agendamento.status}' é um estado final."
                    )
                ),
            }

        atualizado = self.agendamento_repository.update_status(
            agendamento_model, update_status_dto.novo_status
        )

        return {
            "status": "success",
            "message": f"Agendamento atualizado para '{update_status_dto.novo_status}'",
            "data": Agendamento.model_validate(atualizado),
        }
