from use_cases.agendamento.update_status_agendamento.update_status_agendamento_use_case import (
    UpdateStatusAgendamentoUseCase,
)
from use_cases.agendamento.update_status_agendamento.update_status_agendamento_dto import (
    UpdateStatusAgendamentoDTO,
)
from repositories.agendamento_repository import AgendamentoRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db
from uuid import UUID

router = APIRouter()


@router.patch("/agendamentos/{agendamento_id}/status", dependencies=[Depends(validate_user_auth_token)])
def update_status_agendamento(
    agendamento_id: UUID,
    update_status_dto: UpdateStatusAgendamentoDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    agendamento_repository = AgendamentoRepository(db)
    update_status_use_case = UpdateStatusAgendamentoUseCase(agendamento_repository)
    return update_status_use_case.execute(agendamento_id, update_status_dto, response)
