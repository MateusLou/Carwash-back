from repositories.user_repository import UserRepository
from fastapi import Response, Request
from use_cases.user.auth.login.login_dto import LoginDTO
import jwt
import os
import bcrypt


class LoginUseCase:
    """Entra quem sabe a senha do balcão.

    Não há campo de e-mail: o painel roda num computador só, e a senha digitada
    é quem identifica a conta — a do dono abre a plataforma inteira, a da
    equipe abre a operação sem o painel de números. O papel vai dentro do JWT,
    e é ele que o pedágio do painel confere depois.

    Consequência direta do modelo: duas contas ativas não podem ter a mesma
    senha — a de id menor ganharia o login da outra (ver
    UserRepository.list_ativos).
    """

    user_repository: UserRepository

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def execute(self, login_dto: LoginDTO, response: Response, request: Request):
        senha = login_dto.password.encode("utf-8")
        usuario = next(
            (
                conta
                for conta in self.user_repository.list_ativos()
                if bcrypt.checkpw(senha, conta.password.encode("utf-8"))
            ),
            None,
        )

        if usuario is None:
            response.status_code = 400
            return {"status": "error", "message": "Senha incorreta, tente novamente."}

        token = jwt.encode(
            {"email": usuario.email, "id": str(usuario.id), "role": usuario.role},
            os.getenv("USER_JWT_SECRET"),
            algorithm="HS256",
        )

        response.set_cookie(
            key="user_auth_token",
            value=f"Bearer {token}",
            httponly=True,
            samesite="None",
            secure=True,
            path="/",
        )

        response.status_code = 202
        # O papel volta no corpo para a tela decidir aonde levar cada um:
        # dono cai no painel, funcionário cai direto no pátio.
        return {"status": "success", "message": "Acesso permitido", "role": usuario.role}
