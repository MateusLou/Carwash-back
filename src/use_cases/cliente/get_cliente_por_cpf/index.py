from use_cases.cliente.get_cliente_por_cpf.get_cliente_por_cpf_use_case import (
    GetClientePorCpfUseCase,
)
from repositories.cliente_repository import ClienteRepository
from repositories.veiculo_repository import VeiculoRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Path
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/clientes/cpf/{cpf}", dependencies=[Depends(validate_user_auth_token)])
def get_cliente_por_cpf(
    response: Response,
    cpf: str = Path(description="CPF com ou sem pontuação"),
    db: Session = Depends(get_db),
):
    get_cliente_por_cpf_use_case = GetClientePorCpfUseCase(
        ClienteRepository(db), VeiculoRepository(db)
    )
    return get_cliente_por_cpf_use_case.execute(cpf, response)
