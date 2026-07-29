from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
from urllib.parse import quote_plus
import os

load_dotenv()

# O banco é o Postgres do Supabase — o mesmo em que o bot do n8n grava os
# agendamentos. Use a conexão DIRETA (porta 5432), não o pooler em modo
# transaction (6543): o Alembic depende de statements que o pooler não suporta.
DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_NAME = os.getenv("DATABASE_NAME", "postgres")
DATABASE_USERNAME = os.getenv("DATABASE_USERNAME", "postgres")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
DATABASE_SSLMODE = os.getenv("DATABASE_SSLMODE", "require")

# quote_plus na senha: a do Supabase costuma vir com caracteres especiais
# (@, /, #) que quebrariam a URL de conexão se fossem literais.
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
