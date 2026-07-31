import base64
import os
import requests

# A base fica trocável por variável de ambiente para o teste conseguir apontar
# para um servidor local e conferir a requisição sem falar com a Z-API — e sem
# mandar mensagem para cliente de verdade.
URL_BASE_PADRAO = "https://api.z-api.io"

# Quem chama está no meio de um clique no pátio: o funcionário espera esta
# requisição terminar. Seis segundos é o que dá para segurar antes de a tela
# parecer travada.
TIMEOUT_S = 6

# O documento leva mais folga que o texto: o corpo carrega o PDF inteiro em
# base64 (~10 KB de contrato viram ~14 KB de JSON) e a Z-API ainda repassa o
# arquivo ao WhatsApp antes de responder.
TIMEOUT_DOCUMENTO_S = 8


def _credenciais() -> tuple[str, str, str] | None:
    """As três credenciais da Z-API, ou None se qualquer uma faltar.

    Sem credencial não há tentativa de rede. É o desligamento do recurso: em
    dev, o .env vazio garante que ninguém receba mensagem sem querer.
    """
    instancia = os.getenv("ZAPI_INSTANCE_ID")
    token = os.getenv("ZAPI_INSTANCE_TOKEN")
    client_token = os.getenv("ZAPI_CLIENT_TOKEN")

    if not (instancia and token and client_token):
        return None
    return instancia, token, client_token


def _postar(rota: str, corpo: dict, timeout_s: float) -> dict:
    """POST na instância da Z-API. Nunca levanta exceção.

    `rota` é o que vem depois do token na URL ("send-text",
    "send-document/pdf"...). Devolve o mesmo dict das funções públicas.
    """
    credenciais = _credenciais()
    if credenciais is None:
        return {"enviada": False, "motivo": "nao_configurado"}

    if not corpo.get("phone"):
        return {"enviada": False, "motivo": "sem_telefone"}

    instancia, token, client_token = credenciais
    url_base = os.getenv("ZAPI_BASE_URL") or URL_BASE_PADRAO
    url = f"{url_base}/instances/{instancia}/token/{token}/{rota}"

    try:
        resposta = requests.post(
            url,
            headers={"Client-Token": client_token},
            json=corpo,
            timeout=timeout_s,
        )
    except requests.RequestException as erro:
        # Só o tipo do erro: a mensagem da exceção repete a URL, e a URL carrega
        # o token da instância no caminho.
        print(f"Z-API: falha de rede ao enviar WhatsApp ({type(erro).__name__})")
        return {"enviada": False, "motivo": "falha_envio"}

    if resposta.status_code >= 400:
        print(f"Z-API: envio recusado (HTTP {resposta.status_code}): {resposta.text[:200]}")
        return {"enviada": False, "motivo": "falha_envio"}

    return {"enviada": True, "motivo": None}


def enviar_whatsapp(telefone: str, mensagem: str) -> dict:
    """Manda uma mensagem de texto pelo WhatsApp do lava-rápido.

    É a mesma instância da Z-API que o chatbot do n8n usa para conversar: do
    lado do cliente a mensagem chega no mesmo fio, vinda do mesmo número.

    Diferente de `send_email`, esta função **nunca levanta exceção**. Quem chama
    está terminando uma operação que já foi gravada no banco, e uma falha de
    rede não pode desfazer o que aconteceu no pátio — o resultado vem no
    retorno, para a tela contar ao funcionário.

    Args:
        telefone: só dígitos, com o 55 na frente (`5511999998888`) — é o
            formato que a Z-API espera e o que `normalizar_telefone` produz.
        mensagem: texto puro; `\\n` vira quebra de linha no WhatsApp.

    Returns:
        `{"enviada": bool, "motivo": str | None}`, com motivo em
        `nao_configurado`, `sem_telefone` ou `falha_envio`.
    """
    return _postar("send-text", {"phone": telefone, "message": mensagem}, TIMEOUT_S)


def enviar_whatsapp_documento(
    telefone: str, conteudo: bytes, nome_arquivo: str, legenda: str
) -> dict:
    """Manda um PDF pelo mesmo WhatsApp. Mesmo contrato da irmã de texto.

    O arquivo vai **em base64 dentro do corpo** — nenhuma URL do documento é
    criada. É deliberado: o contrato carrega nome, CPF e telefone, e um link
    seria um acesso solto no mundo que não dá para revogar de forma confiável;
    os bytes na conversa são do cliente, e só dele. De quebra, o resultado da
    chamada é a verdade: com URL, quem baixa é o servidor da Z-API depois de a
    gente já ter respondido, e ninguém fica sabendo se deu errado.

    Args:
        telefone: como em `enviar_whatsapp`.
        conteudo: os bytes do PDF.
        nome_arquivo: o nome que aparece na bolha do WhatsApp (sem CPF — bolha
            vira print).
        legenda: o texto que acompanha o documento na conversa.

    Returns:
        `{"enviada": bool, "motivo": str | None}`, mesmos motivos da
        `enviar_whatsapp` — o front reaproveita o mesmo tipo e o mesmo mapa de
        avisos.
    """
    documento = "data:application/pdf;base64," + base64.b64encode(conteudo).decode("ascii")
    corpo = {
        "phone": telefone,
        "document": documento,
        "fileName": nome_arquivo,
        "caption": legenda,
    }
    return _postar("send-document/pdf", corpo, TIMEOUT_DOCUMENTO_S)
