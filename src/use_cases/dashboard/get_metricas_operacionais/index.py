from use_cases.dashboard.get_metricas_operacionais.get_metricas_operacionais_use_case import (
    GetMetricasOperacionaisUseCase,
)
from use_cases.dashboard.periodo_dto import PeriodoDTO, Granularidade
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from datetime import date
from typing import Optional

router = APIRouter()


@router.get("/dashboard/operacional", dependencies=[Depends(validate_user_auth_token)])
def get_metricas_operacionais(
    response: Response,
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    granularidade: Granularidade = Query("mes"),
    db: Session = Depends(get_db),
):
    periodo = PeriodoDTO(data_inicio=data_inicio, data_fim=data_fim, granularidade=granularidade)
    use_case = GetMetricasOperacionaisUseCase(LavagemRepository(db))
    return use_case.execute(periodo, response)
