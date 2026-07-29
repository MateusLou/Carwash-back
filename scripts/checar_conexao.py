"""Confere se o .env aponta para um Supabase alcançável, antes de migrar.

    python scripts/checar_conexao.py

Existe porque os três erros comuns aqui produzem sintomas confusos:

* **conexão direta sem IPv6** → timeout silencioso, sem erro de rede claro;
* **transaction pooler (6543)** → conecta, e só quebra depois, no meio do Alembic;
* **senha errada** → some no meio de um traceback de 40 linhas.

Não escreve nada no banco. A senha nunca é impressa.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

from database.database import DATABASE_URL  # noqa: E402

OK, ALERTA, ERRO = "✅", "⚠️ ", "❌"


def mascarar(url: str) -> str:
    """Devolve a URL sem a senha — o que dá para mostrar na tela e colar num chat."""
    partes = urlparse(url)
    if partes.password:
        return url.replace(partes.password, "•" * 8)
    return url


def main() -> int:
    if not os.getenv("DATABASE_URL") and os.getenv("DATABASE_HOST") in (None, "", "localhost"):
        print(f"{ERRO} O .env não tem DATABASE_URL preenchida.")
        print("   Supabase → Connect → ORMs/URI → aba 'Session pooler', e cole a URI inteira.")
        return 1

    partes = urlparse(DATABASE_URL)
    host, porta = partes.hostname or "", partes.port or 5432

    print(f"destino ....... {mascarar(DATABASE_URL)}")
    print(f"host .......... {host}")
    print(f"porta ......... {porta}")
    print(f"usuário ....... {partes.username}")
    print()

    problemas = []

    if porta == 6543:
        problemas.append(
            f"{ERRO} Porta 6543 é o TRANSACTION pooler. O Alembic não funciona nele "
            "(não mantém prepared statements entre comandos).\n"
            "   Troque para a aba 'Session pooler', porta 5432."
        )

    if host.startswith("db.") and host.endswith(".supabase.co"):
        problemas.append(
            f"{ALERTA} Este é o host da conexão DIRETA, que só tem registro IPv6.\n"
            "   Se esta máquina não tiver rota IPv6, a conexão vai dar timeout sem "
            "mensagem clara. Prefira o Session pooler (*.pooler.supabase.com)."
        )

    if not partes.password:
        problemas.append(f"{ERRO} A URI está sem senha — falta trocar [YOUR-PASSWORD].")

    for problema in problemas:
        print(problema)
    if any(p.startswith(ERRO) for p in problemas):
        return 1
    if problemas:
        print()

    print("conectando…")
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 15})
        with engine.connect() as conexao:
            versao = conexao.execute(text("show server_version")).scalar()
            usuario = conexao.execute(text("select current_user")).scalar()
            banco = conexao.execute(text("select current_database()")).scalar()
            schemas = conexao.execute(
                text(
                    "select nspname from pg_namespace "
                    "where nspname in ('public','operacao') order by 1"
                )
            ).scalars().all()
            tabelas = conexao.execute(
                text(
                    "select table_schema||'.'||table_name from information_schema.tables "
                    "where table_schema in ('public','operacao') order by 1"
                )
            ).scalars().all()
    except Exception as erro:  # noqa: BLE001
        texto = str(erro).lower()
        print(f"{ERRO} não conectou.\n")
        if "timeout" in texto or "could not translate" in texto or "no route" in texto:
            print("   Cheira a rede: host inalcançável daqui. Se for o host direto")
            print("   (db.<ref>.supabase.co), é o problema do IPv6 — use o Session pooler.")
        elif "password authentication failed" in texto:
            print("   A senha do banco está errada. Ela NÃO é a senha da sua conta Supabase:")
            print("   é a Database Password do projeto (dá para redefinir em Settings → Database).")
        elif "tenant or user not found" in texto:
            print("   Usuário/região do pooler não batem. O usuário do Session pooler é")
            print("   postgres.<ref-do-projeto>, e a região está no próprio host.")
        else:
            print(f"   {str(erro).splitlines()[0][:200]}")
        return 1

    print(f"{OK} conectado")
    print(f"   PostgreSQL {versao} | banco {banco} | usuário {usuario}")
    print(f"   schemas presentes: {', '.join(schemas) or 'nenhum'}")
    print()

    do_bot = [t for t in tabelas if t in ("public.agendamentos", "public.conversas")]
    da_plataforma = [t for t in tabelas if t.startswith("operacao.")]

    print(f"tabelas do bot ......... {', '.join(do_bot) if do_bot else 'nenhuma'}")
    if not do_bot:
        print(f"   {ALERTA} rode antes o supabase/schema.sql no SQL Editor")
    print(f"tabelas da plataforma .. {len(da_plataforma)} de 5")
    if not da_plataforma:
        print("   próximo passo: alembic upgrade head")
    elif len(da_plataforma) == 5:
        lavagens = None
        with engine.connect() as conexao:
            lavagens = conexao.execute(text("select count(*) from operacao.lavagens")).scalar()
        print(f"   lavagens já importadas: {lavagens:,}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
