# carwash-back — API da plataforma do Lava-Rápido Nogueira

API em **FastAPI + SQLAlchemy + Alembic** seguindo o template de backend da empresa.
Serve o [carwash-front](../carwash-front) e conversa com **um único Postgres do Supabase**,
dividido em dois schemas:

| Schema | De quem é | Tabelas |
| --- | --- | --- |
| `public` | o chatbot de WhatsApp (n8n) e o login | `agendamentos`, `conversas`, `users` |
| `operacao` | a plataforma | `clientes`, `veiculos`, `funcionarios`, `lavagens`, `importacoes` |

Mesma conexão, dois donos. É o que permite cruzar o agendamento feito pelo WhatsApp com a
lavagem executada — sem misturar as tabelas de quem escreve com as de quem lê.

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
| `src/entities/` | O conceito **para o negócio** (Pydantic). `Lavagem.pode_mudar_para()`, `calcular_nps()`, `Conversa.esta_em_modo_humano()` |
| `src/models/` | O mesmo conceito **para o banco** (SQLAlchemy). Os de `public` espelham [`supabase/schema.sql`](../supabase/schema.sql) |
| `scripts/` | Importador de planilha e diagnóstico de conexão (não fazem parte da API) |
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

Depois preencha a `DATABASE_URL`. O jeito mais seguro é pelo script — a digitação fica
oculta, então a senha não entra no histórico do shell:

```bash
python scripts/configurar_banco.py
```

Ele recusa as três colagens que quebram depois: porta 6543, host direto (IPv6) e a URI com
o `[YOUR-PASSWORD]` ainda por trocar.

Para gerar os segredos da aplicação, caso precise refazê-los:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Qual das três conexões do Supabase usar

| Opção no painel | Porta | Usar? |
| --- | --- | --- |
| **Session pooler** | 5432 | ✅ **esta**. Atende em IPv4 e mantém prepared statements, então o Alembic roda |
| Direct connection | 5432 | só se a máquina tiver IPv6 — `db.<ref>.supabase.co` **não tem registro A** |
| Transaction pooler | 6543 | ❌ o Alembic não funciona: o modo não mantém statements entre comandos |

O sintoma de escolher a direta sem IPv6 é um timeout silencioso na conexão, não um erro
claro de rede. Para saber se a sua máquina tem rota IPv6:

```bash
curl -6 -s -m 5 -o /dev/null -w "%{http_code}\n" https://api64.ipify.org
```

`000` significa sem IPv6 → use o Session pooler.

### Conferindo antes de migrar

```bash
python scripts/checar_conexao.py
```

Diz se a URI está alcançável, qual pooler você pegou, se as tabelas do bot já existem e
quantas lavagens já foram importadas. **Nunca imprime a senha.** Vale rodar antes do
`alembic upgrade head`: os três erros comuns aqui (IPv6, porta 6543, senha) produzem
sintomas confusos, e este script os separa.

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

### Operação — registrar a rotina

| Método | Rota | O que faz |
| --- | --- | --- |
| `POST` | `/lavagens/chegada` | Check-in: telefone, placa, porte. Carimba `chegou_em` e **emite o termo de adesão** |
| `POST` | `/lavagens/{id}/contrato/reenviar` | Manda o termo de novo (aceita `telefone` para corrigir o cadastro) |
| `PATCH` | `/lavagens/{id}/status` | Avança a etapa, carimba o horário e **fecha a duração do trecho** |
| `PATCH` | `/lavagens/{id}/pagamento` | Preço, forma de pagamento e NPS |
| `GET` | `/lavagens/patio` | O que está aberto agora, com o tempo parado em cada etapa |
| `GET` | `/lavagens` | Histórico, com filtros e paginação |
| `GET` | `/clientes?busca=` | Autocomplete do check-in (por nome ou telefone) |

### Dashboard — os números

| Método | Rota | O que faz |
| --- | --- | --- |
| `GET` | `/dashboard/resumo` | Os cards do topo, incluindo NPS e período disponível |
| `GET` | `/dashboard/operacional` | Tempos (média e p90), etapas, produtividade |
| `GET` | `/dashboard/comercial` | Receita, ticket, quebra por pagamento, porte e CNPJ |
| `GET` | `/dashboard/satisfacao` | NPS, distribuição e nota do Google |

Os quatro aceitam `data_inicio`, `data_fim` e `granularidade` (`dia`|`semana`|`mes`).

### Bot de WhatsApp

| Método | Rota | O que faz |
| --- | --- | --- |
| `GET` | `/agendamentos` · `/agendamentos/metricas` | Agendamentos criados pelo chatbot |
| `PATCH` | `/agendamentos/{id}/status` | Confirmar / concluir / cancelar |
| `GET` | `/conversas/modo-humano` | Contatos aguardando um atendente |

**Todas** exigem sessão válida. Sem o cookie respondem **401** — o middleware barra antes
de o use case rodar.

## O termo de adesão do check-in

Logo depois de a chegada ser gravada, o backend **gera o contrato preenchido e manda no
WhatsApp do cliente** — o mesmo "TERMO DE ADESÃO DE PRESTAÇÃO DE SERVIÇOS" do papel, com as
lacunas do PRESTADOR vindas do `.env` e o bloco CLIENTE identificado com o que o atendente
acabou de coletar (nome, CPF, telefone, veículo, serviço, horário e as avarias da vistoria).

As peças, na ordem em que rodam:

| Onde | O quê |
| --- | --- |
| `src/use_cases/lavagem/contrato.py` | **O texto** (as 13 cláusulas, transcritas do PDF original) e a orquestração gera → arquiva → envia. Cláusula muda aqui |
| `src/utils/gerar_pdf.py` | O desenho do A4 (fpdf2). Único arquivo que sabe qual biblioteca de PDF existe |
| `src/utils/storage_contratos.py` | O arquivamento no Supabase Storage (bucket **privado** `contratos`) |
| `src/utils/enviar_whatsapp.py` | `enviar_whatsapp_documento` — o PDF vai em **base64 no corpo**, nenhuma URL é criada |
| `src/entities/vistoria.py` | Os 13 ids de zona do diagrama, espelho do `DiagramaVeiculo.tsx` do front |

Três decisões que valem conhecer:

- **O check-in nunca falha por causa do contrato.** PDF, Storage ou Z-API fora do ar não
  desfazem a chegada: o resultado volta na chave `contrato` da resposta e fica em
  `dados_extras["contrato"]` para diagnóstico. É o mesmo desenho do aviso de "carro pronto".
- **O envio vai em base64, não como link.** O documento carrega nome, CPF e telefone; um link
  assinado em conversa de WhatsApp é um acesso que não se revoga.
- **Sem telefone, o contrato não sai** — a tela avisa, e o card do Pátio ganha o botão
  **Reenviar contrato**, que aceita o número certo e corrige o cadastro junto.

Para desligar: deixe as três `ZAPI_*` em branco (nada é enviado) e/ou as `SUPABASE_*` de
Storage em branco (nada é arquivado). Para testar sem mandar mensagem de verdade:

```bash
python scripts/zapi_falso.py           # Z-API de mentira em localhost:8099
# e no .env: ZAPI_BASE_URL="http://localhost:8099"
```

```bash
python scripts/testar_contrato.py      # gera 6 PDFs de exemplo, sem rede e sem banco
```

O bucket `contratos` se cria no painel do Supabase: **Storage → New bucket → nome
`contratos` → Public bucket DESMARCADO** (o PDF tem CPF; público seria vazamento). CNPJ, RG
e CPF do representante ainda não informados saem como `[CNPJ a informar]` no PDF — preencha
no `.env` quando tiver os documentos.

## Os cinco estados de uma lavagem

Não são decoração: cada transição carimba um horário, e a diferença entre dois carimbos
**é exatamente uma das durações que a base histórica já traz pronta**.

```
aguardando ──inicia──> em_lavagem ──termina──> pronta ──cliente busca──> concluida
    │                        │                    │
 chegou_em            iniciou_lavagem_em   terminou_lavagem_em        saiu_em
    └──── espera ────────────┘                    └──── pós-lavagem ──────┘
```

É isso que faz a lavagem registrada hoje e as 15 mil importadas caírem no mesmo gráfico:
a **duração em minutos é sempre a fonte das métricas**; quem tem carimbo calcula a duração
e grava. Linha importada não tem relógio (os registros viviam no papel) — só duração.

## Importar uma planilha

```bash
python scripts/importar_base.py --arquivo ../dados/base_imputada.xlsx
```

Reimportar o mesmo arquivo não duplica nada: `id_externo` (o `id_lavagem` da planilha) tem
índice único.

Para recarregar do zero, `--recomecar` esvazia `lavagens`, `veiculos`, `clientes`,
`funcionarios` e `importacoes` antes de importar — atrás de confirmação digitada, e sem
tocar no `public` (agendamentos e conversas do bot, e o login). Sem a flag, o script nunca
apaga nada.

O cliente é deduplicado pelo **CPF** quando a planilha traz a coluna, e só cai para o nome
quando não traz. Por nome se perderia gente: a base imputada tem 795 CPFs para 789 nomes,
porque sete pessoas ficaram com o nome "Não informado" — que entra no banco como nulo.

O importador foi feito para a base que **ainda vai chegar**, em três camadas:

1. **Mapa de colunas** — o que a base de hoje tem.
2. **Apelidos** — nomes prováveis do que hoje falta (`telefone`, `placa`, `horario_chegada`,
   `horario_saida`…). Se vierem com um desses nomes, entram na coluna certa sozinhas.
3. **`dados_extras` (jsonb)** — coluna desconhecida não derruba a importação: vai para o
   jsonb e o script avisa no fim quais foram. Depois se decide quais viram coluna própria,
   via migration.

> A base de hoje **não tem telefone nem placa**, e não tem horário de relógio. Esses campos
> existem no banco e nascem vazios; quem os preenche é o check-in, daqui pra frente.

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

A migration tem que sair **vazia** (só um `pass` no `upgrade`). Se vier com alterações em
`agendamentos` ou `conversas`, o model divergiu do `schema.sql` — corrija o model, não o
banco. Depois, apague o arquivo de teste.

> ⚠️ **O filtro de schemas do `env.py` não é opcional.** Para enxergar o schema `operacao`,
> o Alembic precisa de `include_schemas=True` — e com essa flag ligada ele passa a varrer o
> banco inteiro. Um projeto Supabase vem com `auth`, `storage`, `realtime` e `extensions`
> já povoados; sem o `include_name` que restringe a `public` e `operacao`, o autogenerate
> geraria uma migration cheia de `DROP TABLE` em cima da infraestrutura do Supabase.
> Se o `check` acima citar qualquer um desses schemas, **não aplique** — o filtro quebrou.

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
5. **Três pins subidos no `requirements.txt`** (SQLAlchemy 2.0.36, pydantic 2.10.6,
   typing-extensions 4.12.2): os do template não instalam nem rodam em Python 3.13. Cada
   um tem o motivo comentado no arquivo.
6. **Um schema além do `public`** — o template não previa mais de um. O que isso exige do
   Alembic está no aviso acima.
