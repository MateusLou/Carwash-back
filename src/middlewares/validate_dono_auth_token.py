from fastapi import Request, Response, HTTPException
from middlewares.validate_user_auth_token import validate_user_auth_token


def validate_dono_auth_token(request: Request, response: Response):
    """O pedágio do painel de números: além de logado, tem que ser o dono.

    Papel errado recebe 403, não 401 — a sessão está boa, o degrau é que
    falta. Token antigo sem papel (o do workflow do n8n, inclusive) conta como
    funcionário: continua servindo para a operação, só não abre o painel.
    """
    validate_user_auth_token(request, response)

    if request.state.auth_payload.get("role") != "dono":
        raise HTTPException(status_code=403, detail="Somente o dono acessa o painel")

    return True
