from use_cases.importacao.list_importacoes.list_importacoes_use_case import ListImportacoesUseCase
from repositories.importacao_repository import ImportacaoRepository
from middlewares.validate_dono_auth_token import validate_dono_auth_token
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/importacoes", dependencies=[Depends(validate_dono_auth_token)])
def list_importacoes(
    limite: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    list_importacoes_use_case = ListImportacoesUseCase(ImportacaoRepository(db))
    return list_importacoes_use_case.execute(limite)
