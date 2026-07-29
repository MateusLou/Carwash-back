# carwash-back — API do dashboard do Lava-Rápido Nogueira

API em **FastAPI + SQLAlchemy + Alembic** seguindo o template de backend da empresa.
Lê as tabelas `agendamentos` e `conversas` do **Postgres do Supabase** — as mesmas que o
chatbot em n8n escreve — e serve o [carwash-front](../carwash-front).

## Como o código é organizado

O caminho de uma requisição, que é também a ordem das pastas:

```
app.py recebe a chamada
  → middlewares/ confere o login
    → use_cases/ executa a ação (regra de negócio)
      → repositories/ busca ou salva no banco
        → models/ define o formato daquele dado no banco
      ← resposta volta usando a entity
  ← resposta final é devolvida
```

| Pasta | O que mora ali |
| --- | --- |
| `src/app.py` | Sobe o FastAPI, o CORS e **descobre as rotas sozinho** varrendo `use_cases/**/index.py` |
| `src/config/` | O que muda por ambiente (URL do front) |
| `src/database/` | Conexão, sessão e `Base` do SQLAlchemy — a única parte que sabe que o banco é Postgres |
| `src/entities/` | O conceito **para o negócio** (Pydantic). `Agendamento.pode_mudar_para()`, `Conversa.esta_em_modo_humano()` |
| `src/models/` | O mesmo conceito **para o banco** (SQLAlchemy). Espelha [`supabase/schema.sql`](../supabase/schema.sql) |
| `src/repositories/` | A única camada que escreve query |
| `src/use_cases/` | O que o sistema faz — uma subpasta por ação |
| `src/middlewares/` | O porteiro: valida o cookie de sessão antes da rota rodar |
| `src/utils/` | Ferramentas genéricas (hash, senha aleatória, e-mail) |
| `alembic/` | Histórico de mudanças da estrutura do banco |

> **Entity e model são duas classes para a mesma coisa, de propósito**: a entity responde
> "o que é um agendamento para o negócio", o model responde "como ele é guardado". Nada
> garante que as duas fiquem sincronizadas — ao adicionar um campo, mexa **nas duas** (e,
> se for persistido, gere a migration).

## Rodando localmente

### 1. Ambiente e dependências

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

### 2. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha com os dados do Supabase (**Project Settings → Database → Connection string**) e
gere um `USER_JWT_SECRET`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Use a conexão **direta** (porta `5432`), não o pooler em modo transaction (`6543`): o
> Alembic depende de statements que o pooler não suporta bem.

### 3. Banco

```bash
alembic upgrade head
```

Isso cria só a tabela `users`. `agendamentos` e `conversas` já existem — foram criadas pelo
[`supabase/schema.sql`](../supabase/schema.sql) e continuam intactas.

### 4. Subir a API

```bash
uvicorn src.app:app --reload
```

- `http://localhost:8000` → `{"status": "OK"}`
- `http://localhost:8000/docs` → todas as rotas. **Se o `/docs` vier quase vazio**, a
  auto-descoberta falhou: confira o `sys.path` no topo do `src/app.py`.

## Rotas

### Autenticação (vinda do template)

| Método | Rota | O que faz |
| --- | --- | --- |
| `POST` | `/user/auth/register` | Cadastra usuário (`name`, `email`, `password`) |
| `POST` | `/user/auth/login` | Login; devolve o cookie httpOnly `user_auth_token` |
| `POST` | `/user/auth/check/token` | Diz se a sessão ainda vale |
| `POST` | `/user/auth/pwd/recovery/email` | Gera token de recuperação de senha |
| `POST` | `/user/auth/reset/pwd` | Troca a senha usando o token |

### Dashboard (todas exigem sessão válida)

| Método | Rota | O que faz |
| --- | --- | --- |
| `GET` | `/agendamentos` | Lista com filtros `data_inicio`, `data_fim`, `status`, `servico` |
| `GET` | `/agendamentos/metricas` | Totais por status, por serviço e série por dia |
| `PATCH` | `/agendamentos/{id}/status` | Confirmar / concluir / cancelar |
| `GET` | `/conversas/modo-humano` | Contatos ainda aguardando um atendente |

Sem o cookie, essas rotas respondem **401** — o middleware barra antes do use case rodar.

## Migrations

```bash
alembic revision --autogenerate -m "descrição da mudança"
```

**Sempre revise o arquivo gerado antes de aplicar.** O `--autogenerate` acerta ao criar
tabela e adicionar coluna, mas entende uma renomeação como "apagou uma coluna e criou
outra" — o que perde os dados.

```bash
alembic upgrade head     # aplica
alembic downgrade -1     # desfaz a última
```

### Conferindo se os models batem com o Supabase

```bash
alembic revision --autogenerate -m "check"
```

A migration tem que sair **vazia**. Se vier com alterações em `agendamentos` ou
`conversas`, o model divergiu do `schema.sql` — corrija o model, não o banco. Depois,
apague o arquivo de teste.

## Diferenças em relação ao template

1. **Postgres no lugar do MySQL** (`psycopg2-binary`, `postgresql+psycopg2://…?sslmode=require`),
   para falar com o Supabase que o bot já usa.
2. **`sys.path` do `src/` no `app.py`**: os use cases importam `from database.database import …`,
   que só resolve com `src/` no path. Sem isso, rodando `uvicorn src.app:app` da raiz, cada
   rota falharia calada e sumiria do `/docs`.
3. **`alembic/env.py` com um estilo de import só** (`database.database`, não `src.database`):
   misturar os dois cria dois objetos `Base` distintos e o autogenerate enxerga metadata
   incompleta.
4. **CORS restrito ao `client_url`** em vez de `*`: navegador nenhum aceita curinga junto
   com `allow_credentials=True`, e a autenticação aqui é por cookie.
