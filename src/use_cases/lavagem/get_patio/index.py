from use_cases.lavagem.get_patio.get_patio_use_case import GetPatioUseCase
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/lavagens/patio", dependencies=[Depends(validate_user_auth_token)])
def get_patio(response: Response, db: Session = Depends(get_db)):
    get_patio_use_case = GetPatioUseCase(LavagemRepository(db))
    return get_patio_use_case.execute(response)
