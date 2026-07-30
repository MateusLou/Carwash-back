from use_cases.lavagem.vistoria.vistoria_use_case import (
    SalvarVistoriaUseCase,
    GetVistoriaUseCase,
)
from use_cases.lavagem.vistoria.vistoria_dto import SalvarVistoriaDTO
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/lavagens/{lavagem_id}/vistoria", dependencies=[Depends(validate_user_auth_token)])
def get_vistoria(lavagem_id: int, response: Response, db: Session = Depends(get_db)):
    use_case = GetVistoriaUseCase(LavagemRepository(db))
    return use_case.execute(lavagem_id, response)


@router.patch("/lavagens/{lavagem_id}/vistoria", dependencies=[Depends(validate_user_auth_token)])
def salvar_vistoria(
    lavagem_id: int,
    dto: SalvarVistoriaDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    use_case = SalvarVistoriaUseCase(LavagemRepository(db))
    return use_case.execute(lavagem_id, dto, response)
