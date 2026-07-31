from use_cases.agendamento.get_metricas_dashboard.get_metricas_dashboard_use_case import (
    GetMetricasDashboardUseCase,
)
from use_cases.agendamento.get_metricas_dashboard.get_metricas_dashboard_dto import (
    GetMetricasDashboardDTO,
)
from repositories.agendamento_repository import AgendamentoRepository
from middlewares.validate_dono_auth_token import validate_dono_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from datetime import date
from typing import Optional

router = APIRouter()


@router.get("/agendamentos/metricas", dependencies=[Depends(validate_dono_auth_token)])
def get_metricas_dashboard(
    response: Response,
    data_inicio: Optional[date] = Query(None, description="Início do período (AAAA-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Fim do período (AAAA-MM-DD)"),
    db: Session = Depends(get_db),
):
    get_metricas_dto = GetMetricasDashboardDTO(data_inicio=data_inicio, data_fim=data_fim)
    agendamento_repository = AgendamentoRepository(db)
    get_metricas_use_case = GetMetricasDashboardUseCase(agendamento_repository)
    return get_metricas_use_case.execute(get_metricas_dto, response)
