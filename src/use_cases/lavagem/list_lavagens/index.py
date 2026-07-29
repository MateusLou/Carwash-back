from use_cases.lavagem.list_lavagens.list_lavagens_use_case import ListLavagensUseCase
from use_cases.lavagem.list_lavagens.list_lavagens_dto import ListLavagensDTO
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from datetime import date
from typing import Optional

router = APIRouter()


@router.get("/lavagens", dependencies=[Depends(validate_user_auth_token)])
def list_lavagens(
    response: Response,
    data_inicio: Optional[date] = Query(None, description="A partir desta data (AAAA-MM-DD)"),
    data_fim: Optional[date] = Query(None, description="Até esta data (AAAA-MM-DD)"),
    status: Optional[str] = Query(None, description="aguardando | em_lavagem | pronta | concluida | cancelada"),
    funcionario_id: Optional[int] = None,
    tipo_carro: Optional[str] = None,
    cliente_id: Optional[int] = None,
    limite: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    list_dto = ListLavagensDTO(
        data_inicio=data_inicio,
        data_fim=data_fim,
        status=status,
        funcionario_id=funcionario_id,
        tipo_carro=tipo_carro,
        cliente_id=cliente_id,
        limite=limite,
        offset=offset,
    )
    list_lavagens_use_case = ListLavagensUseCase(LavagemRepository(db))
    return list_lavagens_use_case.execute(list_dto, response)
