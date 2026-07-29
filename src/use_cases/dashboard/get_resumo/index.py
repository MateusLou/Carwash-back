from use_cases.dashboard.get_resumo.get_resumo_use_case import GetResumoUseCase
from use_cases.dashboard.periodo_dto import PeriodoDTO, Granularidade
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from datetime import date
from typing import Optional

router = APIRouter()


@router.get("/dashboard/resumo", dependencies=[Depends(validate_user_auth_token)])
def get_resumo(
    response: Response,
    data_inicio: Optional[date] = Query(None, description="Início do período (AAAA-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Fim do período (AAAA-MM-DD)"),
    granularidade: Granularidade = Query("mes", description="dia | semana | mes"),
    db: Session = Depends(get_db),
):
    periodo = PeriodoDTO(data_inicio=data_inicio, data_fim=data_fim, granularidade=granularidade)
    get_resumo_use_case = GetResumoUseCase(LavagemRepository(db))
    return get_resumo_use_case.execute(periodo, response)
