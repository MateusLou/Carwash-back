from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

# O banco é o Postgres do Supabase — o mesmo em que o bot do n8n grava os
# agendamentos.
#
# Qual conexão usar, no painel do Supabase (Connect → ORMs/URI):
#   • Session pooler (porta 5432) — é a que funciona em rede só-IPv4, que é o
#     caso da maioria das máquinas. Suporta prepared statements, então o Alembic
#     roda normal.
#   • Direct connection (porta 5432, host db.<ref>.supabase.co) — só resolve em
#     IPv6. Sem rota IPv6 a conexão nem chega a ser tentada.
#   • Transaction pooler (porta 6543) — NÃO use: o Alembic depende de statements
#     que esse modo não mantém entre comandos.
#
# Duas formas de configurar, e a DATABASE_URL ganha quando as duas existem:
# colar a URI inteira do painel é menos sujeito a erro do que remontar cinco
# campos na mão.
DATABASE_URL_BRUTA = os.getenv("DATABASE_URL", "").strip()

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "postgres")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require")


def _normalizar(url: str) -> str:
    """Aceita a URI como o Supabase a entrega e devolve o que o SQLAlchemy quer.

    Duas correções que o copiar-e-colar sempre precisa: o esquema (o painel dá
    `postgresql://`, e alguns lugares ainda dão `postgres://`, que o SQLAlchemy
    2 recusa) e o `sslmode`, que o Supabase exige mas não vem na string.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    if "sslmode=" not in url:
        url += ("&" if "?" in url else "?") + f"sslmode={DATABASE_SSLMODE}"
    return url


if DATABASE_URL_BRUTA:
    DATABASE_URL = _normalizar(DATABASE_URL_BRUTA)
else:
    # quote_plus na senha e no usuário: a senha do Supabase costuma ter
    # caracteres especiais (@, /, #) que quebrariam a URL se fossem literais.
    DATABASE_URL = (
        f"postgresql+psycopg2://{quote_plus(DATABASE_USERNAME)}:{quote_plus(DATABASE_PASSWORD)}"
        f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}?sslmode={DATABASE_SSLMODE}"
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency para FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
