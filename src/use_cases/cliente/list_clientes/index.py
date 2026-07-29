from use_cases.cliente.list_clientes.list_clientes_use_case import ListClientesUseCase
from repositories.cliente_repository import ClienteRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response, Query
from sqlalchemy.orm import Session
from database.database import get_db
from typing import Optional

router = APIRouter()


@router.get("/clientes", dependencies=[Depends(validate_user_auth_token)])
def list_clientes(
    response: Response,
    busca: Optional[str] = Query(None, description="Parte do nome ou do telefone"),
    db: Session = Depends(get_db),
):
    list_clientes_use_case = ListClientesUseCase(ClienteRepository(db))
    return list_clientes_use_case.execute(busca, response)
