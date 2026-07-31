from fastapi import Response, Request


class CheckSessionValidityUseCase:
    def execute(self, response: Response, request: Request):
        # O papel volta junto: é como o front decide o que mostrar no menu.
        # Sessão antiga (token sem papel) vem role=None — vale como funcionário.
        return {
            "status": "success",
            "message": "Autenticação é válida para acessar a página do usuário",
            "role": request.state.auth_payload.get("role"),
        }
