from use_cases.agendamento.list_agendamentos.list_agendamentos_use_case import ListAgendamentosUseCase
from use_cases.agendamento.list_agendamentos.list_agendamentos_dto import ListAgendamentosDTO
from repositories.agendamento_repository import AgendamentoRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from datetime import date
from typing import Optional

router = APIRouter()


@router.get("/agendamentos", dependencies=[Depends(validate_user_auth_token)])
def list_agendamentos(
    response: Response,
    data_inicio: Optional[date] = Query(None, description="Filtra a partir desta data (AAAA-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Filtra até esta data (AAAA-MM-DD)"),
    status: Optional[str] = Query(None, description="pendente | confirmado | concluido | cancelado"),
    servico: Optional[str] = Query(None, description="Nome exato do serviço"),
    db: Session = Depends(get_db),
):
    list_agendamentos_dto = ListAgendamentosDTO(
        data_inicio=data_inicio, data_fim=data_fim, status=status, servico=servico
    )
    agendamento_repository = AgendamentoRepository(db)
    list_agendamentos_use_case = ListAgendamentosUseCase(agendamento_repository)
    return list_agendamentos_use_case.execute(list_agendamentos_dto, response)
