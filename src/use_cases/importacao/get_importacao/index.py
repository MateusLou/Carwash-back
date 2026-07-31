from use_cases.importacao.get_importacao.get_importacao_use_case import GetImportacaoUseCase
from repositories.importacao_repository import ImportacaoRepository
from middlewares.validate_dono_auth_token import validate_dono_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/importacoes/{importacao_id}", dependencies=[Depends(validate_dono_auth_token)])
def get_importacao(
    importacao_id: int,
    response: Response,
    db: Session = Depends(get_db),
):
    get_importacao_use_case = GetImportacaoUseCase(ImportacaoRepository(db))
    return get_importacao_use_case.execute(importacao_id, response)
