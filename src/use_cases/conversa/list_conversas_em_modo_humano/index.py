from use_cases.conversa.list_conversas_em_modo_humano.list_conversas_em_modo_humano_use_case import (
    ListConversasEmModoHumanoUseCase,
)
from repositories.conversa_repository import ConversaRepository
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from database.database import get_db

router = APIRouter()


@router.get("/conversas/modo-humano", dependencies=[Depends(validate_user_auth_token)])
def list_conversas_em_modo_humano(response: Response, db: Session = Depends(get_db)):
    conversa_repository = ConversaRepository(db)
    list_conversas_use_case = ListConversasEmModoHumanoUseCase(conversa_repository)
    return list_conversas_use_case.execute(response)
