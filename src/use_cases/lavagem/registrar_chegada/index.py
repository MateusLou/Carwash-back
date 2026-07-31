from use_cases.lavagem.registrar_chegada.registrar_chegada_use_case import RegistrarChegadaUseCase
from use_cases.lavagem.registrar_chegada.registrar_chegada_dto import RegistrarChegadaDTO
from repositories.lavagem_repository import LavagemRepository
from repositories.cliente_repository import ClienteRepository
from repositories.veiculo_repository import VeiculoRepository
from repositories.agendamento_repository import AgendamentoRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.post("/lavagens/chegada", dependencies=[Depends(validate_user_auth_token)])
def registrar_chegada(
    chegada_dto: RegistrarChegadaDTO,
    response: Response,
    db: Session = Depends(get_db),
):
    registrar_chegada_use_case = RegistrarChegadaUseCase(
        LavagemRepository(db),
        ClienteRepository(db),
        VeiculoRepository(db),
        AgendamentoRepository(db),
    )
    return registrar_chegada_use_case.execute(chegada_dto, response)
