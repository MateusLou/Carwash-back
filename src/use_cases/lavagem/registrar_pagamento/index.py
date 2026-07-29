from use_cases.lavagem.registrar_pagamento.registrar_pagamento_use_case import (
    RegistrarPagamentoUseCase,
)
from use_cases.lavagem.registrar_pagamento.registrar_pagamento_dto import RegistrarPagamentoDTO
from repositories.lavagem_repository import LavagemRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.patch("/lavagens/{lavagem_id}/pagamento", dependencies=[Depends(validate_user_auth_token)])
def registrar_pagamento(
    lavagem_id: int,
    pagamento_dto: RegistrarPagamentoDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    registrar_pagamento_use_case = RegistrarPagamentoUseCase(LavagemRepository(db))
    return registrar_pagamento_use_case.execute(lavagem_id, pagamento_dto, response)
