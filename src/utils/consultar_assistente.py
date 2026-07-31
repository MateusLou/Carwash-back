import os
import requests

# O agente do n8n encadeia Gemini + ferramentas (RAG e RPCs no Supabase) antes
# de responder — 20 a 30 segundos é normal numa pergunta com consulta. O front
# mostra "Pensando…" enquanto isso; 60s é o teto antes de assumir que caiu.
# Se um dia houver proxy na frente do backend (nginx, Heroku), alinhe lá também.
TIMEOUT_S = 60


def _credenciais() -> tuple[str, str] | None:
    """A URL do webhook e o token compartilhado, ou None se qualquer um faltar.

    Sem credencial não há tentativa de rede. É o desligamento do recurso: em
    dev, o .env vazio faz a aba do assistente responder "não configurado" em
    vez de quebrar — mesmo contrato da Z-API em `enviar_whatsapp`.
    """
    url = os.getenv("N8N_ASSISTENTE_WEBHOOK_URL")
    token = os.getenv("N8N_ASSISTENTE_TOKEN")

    if not (url and token):
        return None
    return url, token


def consultar_assistente(mensagem: str, sessao: str) -> dict:
    """Pergunta ao assistente de gestão (workflow do n8n) e espera a resposta.

    O webhook (`n8n/workflow-assistente-gestao.json`) responde na MESMA
    requisição HTTP: o corpo volta como `{"resposta": "..."}`. A autenticação
    é o header `X-Assistente-Token`, que precisa bater com o valor chumbado no
    nó "Token válido?" do workflow.

    Nunca levanta exceção: quem chama está no meio de uma conversa e precisa
    de algo para mostrar na tela — o resultado diz o que houve.

    Args:
        mensagem: a pergunta do usuário, texto puro.
        sessao: chave da memória de conversa no n8n (uma por usuário do
            painel, ex.: "assistente-3"). O prefixo evita colisão com as
            sessões-telefone do bot de WhatsApp, que vivem na mesma instância.

    Returns:
        `{"ok": bool, "resposta": str | None, "motivo": str | None}`, com
        motivo em `nao_configurado`, `token_invalido`, `falha_comunicacao`
        ou `resposta_invalida`.
    """
    credenciais = _credenciais()
    if credenciais is None:
        return {"ok": False, "resposta": None, "motivo": "nao_configurado"}

    url, token = credenciais

    try:
        resposta = requests.post(
            url,
            headers={"X-Assistente-Token": token},
            json={"mensagem": mensagem, "sessao": sessao},
            timeout=TIMEOUT_S,
        )
    except requests.RequestException as erro:
        # Só o tipo do erro: a mensagem da exceção repete a URL do webhook,
        # que não precisa aparecer em log.
        print(f"Assistente: falha de rede ao consultar o n8n ({type(erro).__name__})")
        return {"ok": False, "resposta": None, "motivo": "falha_comunicacao"}

    if resposta.status_code == 401:
        # O n8n recusou o token — o valor do .env não bate com o do workflow.
        print("Assistente: n8n recusou o token (HTTP 401)")
        return {"ok": False, "resposta": None, "motivo": "token_invalido"}

    if resposta.status_code >= 400:
        print(f"Assistente: n8n respondeu HTTP {resposta.status_code}: {resposta.text[:200]}")
        return {"ok": False, "resposta": None, "motivo": "falha_comunicacao"}

    try:
        corpo = resposta.json()
    except ValueError:
        print("Assistente: resposta do n8n não é JSON")
        return {"ok": False, "resposta": None, "motivo": "resposta_invalida"}

    texto = corpo.get("resposta") if isinstance(corpo, dict) else None
    if not isinstance(texto, str) or not texto.strip():
        # Workflow no ar mas com o fluxo quebrado (ex.: agente sem credencial).
        print("Assistente: resposta do n8n sem o campo 'resposta'")
        return {"ok": False, "resposta": None, "motivo": "resposta_invalida"}

    return {"ok": True, "resposta": texto.strip(), "motivo": None}
