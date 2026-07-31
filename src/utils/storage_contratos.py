"""Supabase Storage, pela REST — só o que o contrato precisa.

Deliberadamente pequeno e fechado nestas duas funções. Se um dia o 1 GB do plano
free apertar, trocar o Supabase por outro armazenamento é reescrever este arquivo
e nada mais: nenhum use case sabe que existe um bucket do outro lado.

Não usamos o SDK `supabase` — ele arrasta postgrest e realtime, que este projeto
resolve pelo SQLAlchemy. Nem `httpx`, que está no venv como dependência do
FastAPI mas não no `requirements.txt`: `requests` já é declarado e já é o cliente
HTTP de saída do projeto (`enviar_whatsapp`). Dois clientes para duas chamadas
seria peça móvel a mais.

**O bucket é privado.** O objeto guardado aqui tem nome, CPF e telefone do
cliente; um bucket público seria um vazamento de dado pessoal aberto na internet.
No painel: Storage > New bucket, nome `contratos`, **Public bucket DESMARCADO**.
"""

import os

import requests

# Uma ida ao Storage é uma ida aos Estados Unidos — o projeto Supabase deste
# lava-rápido está em us-west-2. Cinco segundos é o que dá para segurar dentro de
# um check-in que o atendente está esperando terminar.
TIMEOUT_S = 5

# O mesmo prazo que o `cache-control` do objeto pede. Guardar por muito tempo na
# borda alonga a janela em que um objeto já apagado continua sendo servido.
TTL_CACHE_S = 300


class StorageIndisponivel(RuntimeError):
    """Configuração ausente ou Storage recusando.

    Existe para que um erro de rede não suba cru até o FastAPI: sem esta
    tradução, um `ConnectionError` viraria **500**, e o celular do atendente
    receberia "Internal Server Error" no meio do check-in, sem nenhuma pista de
    que o problema é a rede e de que vale tentar de novo.
    """


def _credenciais() -> tuple[str, str, str] | None:
    url = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
    chave = (os.getenv("SUPABASE_SERVICE_KEY") or "").strip()
    bucket = (os.getenv("SUPABASE_BUCKET_CONTRATOS") or "contratos").strip()

    if not (url and chave):
        return None
    return url, chave, bucket


def esta_configurado() -> bool:
    """Sem as duas variáveis não há tentativa de rede.

    É o desligamento do arquivamento: em dev, o `.env` vazio faz o contrato ser
    gerado e enviado normalmente, só não guardado.
    """
    return _credenciais() is not None


def salvar(caminho: str, conteudo: bytes, content_type: str = "application/pdf") -> str:
    """Grava o objeto e devolve o caminho gravado.

    `x-upsert: false` de propósito: o caminho carrega um UUID, então colisão é
    bug, não concorrência — e sobrescrever em silêncio apagaria um contrato que
    já foi entregue a um cliente.
    """
    credenciais = _credenciais()
    if credenciais is None:
        raise StorageIndisponivel(
            "SUPABASE_URL e SUPABASE_SERVICE_KEY não estão no .env do backend."
        )

    url_base, chave, bucket = credenciais

    try:
        resposta = requests.post(
            f"{url_base}/storage/v1/object/{bucket}/{caminho}",
            headers={
                "Authorization": f"Bearer {chave}",
                "apikey": chave,
                "Content-Type": content_type,
                "x-upsert": "false",
                "cache-control": f"max-age={TTL_CACHE_S}",
            },
            data=conteudo,
            timeout=TIMEOUT_S,
        )
    except requests.RequestException as erro:
        # Só o tipo do erro: a mensagem da exceção repete a URL, e a URL do
        # Supabase aparece junto do header que carrega a service key nos logs de
        # quem for depurar por cima.
        raise StorageIndisponivel(
            f"Não foi possível falar com o Supabase Storage ({type(erro).__name__})."
        ) from None

    if resposta.status_code >= 400:
        # Status e corpo, nunca a chave.
        raise StorageIndisponivel(
            f"Supabase Storage recusou o upload: HTTP {resposta.status_code} "
            f"{resposta.text[:200]}"
        )

    return caminho
