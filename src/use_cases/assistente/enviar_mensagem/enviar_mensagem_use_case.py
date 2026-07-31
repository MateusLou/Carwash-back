from fastapi import Request, Response

from use_cases.assistente.enviar_mensagem.enviar_mensagem_dto import EnviarMensagemDTO
from utils.consultar_assistente import consultar_assistente

# A mensagem vira contexto do Gemini e memória de conversa no n8n.
TAMANHO_MAXIMO = 2000

# O que cada falha do util vira na tela. Nenhuma vira 401: o front redireciona
# qualquer 401 para o /login, e um token errado no n8n derrubaria a sessão do
# usuário — que está logado normalmente.
_ERROS = {
    "nao_configurado": (
        503,
        "O assistente ainda não foi configurado neste ambiente. "
        "Preencha N8N_ASSISTENTE_WEBHOOK_URL e N8N_ASSISTENTE_TOKEN no .env.",
    ),
    "token_invalido": (
        502,
        "O assistente recusou a conexão. Confira se o token do .env é o mesmo "
        "do nó 'Token válido?' no workflow do n8n.",
    ),
    "falha_comunicacao": (
        502,
        "O assistente está fora do ar. Tente de novo em instantes.",
    ),
    "resposta_invalida": (
        502,
        "O assistente respondeu de um jeito inesperado. Confira o workflow no n8n.",
    ),
}


class EnviarMensagemUseCase:
    """Repassa a pergunta do painel ao workflow do n8n e devolve a resposta.

    Não toca o banco: o cérebro (agente, memória, ferramentas de consulta)
    vive no n8n. Aqui é só a ponte autenticada — o webhook não fica exposto
    ao navegador e o token compartilhado nunca chega ao front.

    A rota é síncrona e segura uma thread do pool por até 60s por pergunta.
    Para um painel de um proprietário isso é irrelevante; se um dia virar
    multiusuário intenso, é o primeiro lugar para revisitar.
    """

    def execute(self, dto: EnviarMensagemDTO, response: Response, request: Request):
        mensagem = dto.mensagem.strip()

        if not mensagem:
            response.status_code = 422
            return {"status": "error", "message": "Escreva uma pergunta para o assistente."}

        if len(mensagem) > TAMANHO_MAXIMO:
            response.status_code = 422
            return {
                "status": "error",
                "message": f"A pergunta passou de {TAMANHO_MAXIMO} caracteres. Resuma e tente de novo.",
            }

        # Uma memória de conversa por usuário do painel. O prefixo separa das
        # sessões-telefone do bot de WhatsApp (a memória buffer é global na
        # instância do n8n).
        auth = getattr(request.state, "auth_payload", None) or {}
        sessao = f"assistente-{auth.get('user_id') or 'painel'}"

        resultado = consultar_assistente(mensagem, sessao)

        if not resultado["ok"]:
            status, texto = _ERROS.get(resultado["motivo"], _ERROS["falha_comunicacao"])
            response.status_code = status
            return {"status": "error", "message": texto}

        return {"status": "success", "data": {"resposta": resultado["resposta"]}}
