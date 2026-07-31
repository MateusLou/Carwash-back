from use_cases.lavagem.reenviar_contrato.reenviar_contrato_use_case import (
    ReenviarContratoUseCase,
)
from use_cases.lavagem.reenviar_contrato.reenviar_contrato_dto import ReenviarContratoDTO
from repositories.lavagem_repository import LavagemRepository
from repositories.cliente_repository import ClienteRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.post(
    "/lavagens/{lavagem_id}/contrato/reenviar",
    dependencies=[Depends(validate_user_auth_token)],
)
def reenviar_contrato(
    lavagem_id: int,
    dto: ReenviarContratoDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    use_case = ReenviarContratoUseCase(
        LavagemRepository(db),
        ClienteRepository(db),
    )
    return use_case.execute(lavagem_id, dto, response)
