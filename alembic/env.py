from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import sys
from pathlib import Path

# Adiciona o diretório src ao path.
# A partir daqui os imports usam o MESMO estilo do resto do projeto
# ("from database.database import ..."). Misturar "src.database" com
# "database" criaria dois objetos Base diferentes, e o autogenerate
# enxergaria só metade dos models.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importa o Base e TODOS os models.
# O import de "models" puxa o __init__.py, que registra cada model no Base —
# sem isso o autogenerate compara contra uma metadata vazia e sai em branco.
from database.database import Base, DATABASE_URL
import models  # noqa: F401

target_metadata = Base.metadata

# A senha pode conter "%", que o ConfigParser do Alembic leria como
# interpolação — por isso o escape antes de gravar na config.
config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))


# Os únicos schemas que este projeto gerencia. None = o schema padrão (public).
SCHEMAS_GERENCIADOS = {None, "public", "operacao"}

# Tabelas que vivem no `public` mas NÃO são geridas por este ORM: elas nascem e
# morrem no supabase/schema.sql. Sem este filtro, o autogenerate as vê como
# "sobrando" na metadata e emite `op.drop_table` para cada uma.
#
# Por que isso é grave: `agenda_config` é lida pelo trigger
# `agendamentos_limite_capacidade` a CADA insert em `agendamentos`. Se a tabela
# some, o trigger levanta 42P01 e o chatbot para de agendar por completo — e a
# RPC `agenda_criar_agendamento` só captura P0001, então o erro sobe cru.
PREFIXOS_FORA_DO_ORM = ("agenda_",)


def include_name(name, type_, parent_names):
    """Filtra o que o autogenerate enxerga.

    Sem isso, `include_schemas=True` faz o Alembic varrer o banco INTEIRO — e um
    projeto Supabase vem com `auth`, `storage`, `realtime`, `extensions` e
    `graphql` já povoados. O autogenerate os veria como tabelas "sobrando" na
    metadata e geraria uma migration cheia de DROP TABLE em cima da
    infraestrutura do Supabase. Ligar a flag sem este filtro é destrutivo.
    """
    if type_ == "schema":
        return name in SCHEMAS_GERENCIADOS
    if type_ == "table" and name is not None:
        return not name.startswith(PREFIXOS_FORA_DO_ORM)
    return True


# Opções compartilhadas entre os modos offline e online — para as duas rodadas
# enxergarem exatamente os mesmos schemas.
opcoes_contexto = {
    "target_metadata": target_metadata,
    "include_schemas": True,
    "include_name": include_name,
    "compare_type": True,
}


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **opcoes_contexto,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, **opcoes_contexto)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
