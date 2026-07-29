from use_cases.lavagem.avancar_status_lavagem.avancar_status_lavagem_use_case import (
    AvancarStatusLavagemUseCase,
)
from use_cases.lavagem.avancar_status_lavagem.avancar_status_lavagem_dto import (
    AvancarStatusLavagemDTO,
)
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.patch("/lavagens/{lavagem_id}/status", dependencies=[Depends(validate_user_auth_token)])
def avancar_status_lavagem(
    lavagem_id: int,
    avancar_dto: AvancarStatusLavagemDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    avancar_status_use_case = AvancarStatusLavagemUseCase(LavagemRepository(db))
    return avancar_status_use_case.execute(lavagem_id, avancar_dto, response)
