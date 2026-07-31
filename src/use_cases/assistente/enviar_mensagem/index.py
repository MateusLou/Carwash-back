from use_cases.assistente.enviar_mensagem.enviar_mensagem_use_case import (
    EnviarMensagemUseCase,
)
from use_cases.assistente.enviar_mensagem.enviar_mensagem_dto import EnviarMensagemDTO
from middlewares.validate_user_auth_token import validate_user_auth_token
from fastapi import APIRouter, Depends, Request, Response

router = APIRouter()


@router.post(
    "/assistente/mensagem",
    dependencies=[Depends(validate_user_auth_token)],
)
def enviar_mensagem(
    dto: EnviarMensagemDTO,
    response: Response,
    request: Request,
):
    use_case = EnviarMensagemUseCase()
    return use_case.execute(dto, response, request)
