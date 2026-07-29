"""Grava a URI do Supabase no .env sem ela aparecer em lugar nenhum.

    python scripts/configurar_banco.py

A URI contém a senha do banco. Digitada num prompt oculto, ela não entra no
histórico do shell, não aparece na tela e não passa por nenhum log — só vai para
o .env, que tem permissão 600 e está no .gitignore.

Antes de gravar, confere o formato e recusa as duas escolhas que quebram depois:
a porta 6543 (transaction pooler, incompatível com o Alembic) e o host direto
db.<ref>.supabase.co (só IPv6).
"""

import re
import sys
from getpass import getpass
from pathlib import Path
from urllib.parse import urlparse

RAIZ = Path(__file__).resolve().parent.parent
ARQUIVO_ENV = RAIZ / ".env"

OK, ALERTA, ERRO = "✅", "⚠️ ", "❌"


def mascarar(url: str) -> str:
    partes = urlparse(url)
    return url.replace(partes.password, "•" * 8) if partes.password else url


def validar(url: str) -> list[str]:
    """Devolve a lista de erros. Vazia = pode gravar."""
    erros = []

    # Antes de qualquer parsing: o painel entrega a URI com [YOUR-PASSWORD], e é
    # o erro mais provável de todos. Os colchetes também fariam o urlparse achar
    # que o host é um endereço IPv6 e estourar com um ValueError ilegível.
    if re.search(r"\[[^\]]*\]", url):
        return [
            f"{ERRO} A URI ainda tem o marcador entre colchetes que o painel deixa\n"
            "   ([YOUR-PASSWORD]). Troque esse trecho pela Database Password do\n"
            "   projeto — Settings → Database (não é a senha da sua conta Supabase)."
        ]

    try:
        partes = urlparse(url)
    except ValueError as erro:
        return [f"{ERRO} Não consegui interpretar a URI: {erro}"]

    if partes.scheme not in ("postgres", "postgresql", "postgresql+psycopg2"):
        erros.append(
            f"{ERRO} Não parece uma URI de Postgres (começa com "
            f"{partes.scheme or '???'}://).\n"
            "   O que se cola aqui começa com postgresql://"
        )
        return erros  # sem esquema válido, o resto da análise não vale nada

    if not partes.hostname:
        erros.append(f"{ERRO} URI sem host.")
    if not partes.password or partes.password.upper().startswith("%5BYOUR"):
        erros.append(
            f"{ERRO} Falta a senha — o painel entrega a URI com [YOUR-PASSWORD] no lugar.\n"
            "   Troque esse trecho pela Database Password do projeto "
            "(Settings → Database)."
        )
    if partes.port == 6543:
        erros.append(
            f"{ERRO} Porta 6543 é o TRANSACTION pooler, e o Alembic não roda nele.\n"
            "   No painel: aba Session pooler (porta 5432). No snippet do Prisma, é a\n"
            "   segunda URL — a do comentário 'session pooler', que ele chama de DIRECT_URL."
        )
    if (partes.hostname or "").startswith("db.") and (partes.hostname or "").endswith(
        ".supabase.co"
    ):
        erros.append(
            f"{ERRO} Este é o host da conexão DIRETA, que só tem endereço IPv6 — e esta\n"
            "   máquina não tem rota IPv6. Use o host *.pooler.supabase.com."
        )
    return erros


def gravar(url: str) -> None:
    """Troca a linha DATABASE_URL do .env, preservando todo o resto."""
    if not ARQUIVO_ENV.exists():
        print(f"{ERRO} {ARQUIVO_ENV} não existe. Rode antes: cp .env.example .env")
        raise SystemExit(1)

    linhas = ARQUIVO_ENV.read_text(encoding="utf8").splitlines()
    saida, trocou = [], False
    for linha in linhas:
        if re.match(r"\s*DATABASE_URL\s*=", linha) and not linha.lstrip().startswith("#"):
            saida.append(f'DATABASE_URL="{url}"')
            trocou = True
        else:
            saida.append(linha)
    if not trocou:
        saida.append(f'DATABASE_URL="{url}"')

    ARQUIVO_ENV.write_text("\n".join(saida) + "\n", encoding="utf8")
    ARQUIVO_ENV.chmod(0o600)


def main() -> int:
    print("Cole a URI do Supabase (Connect → aba Session pooler, porta 5432).")
    print("A digitação fica oculta de propósito — a senha está dentro da URI.\n")

    url = (getpass("URI: ") if sys.stdin.isatty() else sys.stdin.readline()).strip()
    if not url:
        print(f"{ERRO} Nada foi colado.")
        return 1

    # tira aspas e um eventual "DATABASE_URL=" colado junto
    url = re.sub(r'^\s*(export\s+)?DATABASE_URL\s*=\s*', "", url).strip().strip("\"'")

    erros = validar(url)
    if erros:
        print()
        for erro in erros:
            print(erro)
        print(f"\nNada foi gravado. O .env continua como estava.")
        return 1

    partes = urlparse(url)
    gravar(url)

    print(f"\n{OK} gravado em {ARQUIVO_ENV}")
    print(f"   {mascarar(url)}")
    print(f"   host {partes.hostname} · porta {partes.port or 5432} · usuário {partes.username}")
    print("\nPróximo passo:  python scripts/checar_conexao.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
