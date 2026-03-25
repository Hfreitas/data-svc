# data-svc

Microserviço HTTP que isola o acesso ao banco de dados do N8N. Substitui chamadas diretas do N8N ao Supabase, adicionando cache em memória e uma camada de abstração testável.

```
Antes:  N8N ──────────────────────────→ Supabase
Depois: N8N ──→ data-svc (Flask) ──→ Supabase
                        ↑
                   cache em memória
```

**Stack:** Python 3.12 · Flask · psycopg2 · cachetools · Gunicorn

---

## Contribuição

### Regras obrigatórias

- **Push direto na `main` é proibido.** Todo código deve chegar via Pull Request.
- **Todo PR precisa de ao menos 1 aprovação** do responsável técnico antes de ser mergeado.
- PRs com conflito com a `main` não serão revisados — resolva o conflito primeiro.

### Fluxo de trabalho

```bash
# 1. Atualize sua main local antes de começar
git checkout main
git pull origin main

# 2. Crie uma branch descritiva a partir da main
git checkout -b feat/usuarios-get-endpoint

# 3. Desenvolva, commite com mensagens claras
git add src/routes/usuarios.py src/queries/usuarios.py
git commit -m "feat: implementa GET /usuarios com cache TTL 60s"

# 4. Envie a branch e abra o PR
git push origin feat/usuarios-get-endpoint
gh pr create --title "feat: GET /usuarios" --body "Descrição do que foi feito"
```

### Nomenclatura de branches

| Tipo | Padrão | Exemplo |
|---|---|---|
| Nova funcionalidade | `feat/<descricao>` | `feat/comprovantes-post` |
| Correção de bug | `fix/<descricao>` | `fix/cache-invalidation-saldo` |
| Testes | `test/<descricao>` | `test/usuarios-suite` |
| Documentação | `docs/<descricao>` | `docs/setup-docker` |

### O que incluir no PR

- O que foi implementado e por quê
- Como testar localmente (comando curl ou pytest)
- Se adicionou dependência nova, justificar

---

## Estrutura de pastas

```
data-svc/
├── src/
│   ├── app.py          # Flask factory — registra blueprints e inicializa dependências
│   ├── config.py       # Variáveis de ambiente com validação (falha rápido se DATABASE_URL ausente)
│   ├── db.py           # Pool de conexões psycopg2 + context manager get_db_conn()
│   ├── cache.py        # TTLCache em memória — get, set e invalidate por namespace
│   │
│   ├── routes/         # Blueprints Flask — validação de entrada, cache, formatação de saída
│   │   ├── usuarios.py         # GET /usuarios  POST /usuarios  PUT /usuarios/<id>
│   │   ├── comprovantes.py     # GET /saldo  GET /comprovantes  POST /comprovantes
│   │   ├── agendamentos.py     # GET /agendamentos  POST /agendamentos  PUT /agendamentos/<id>
│   │   ├── listas.py           # GET /listas  GET/POST/DELETE /listas/<id>/itens
│   │   └── contas.py           # POST /contas-recorrentes
│   │
│   ├── queries/        # SQL puro — funções que recebem conn + params e retornam dicts
│   │   ├── usuarios.py
│   │   ├── comprovantes.py
│   │   ├── agendamentos.py
│   │   ├── listas.py
│   │   └── contas.py
│   │
│   └── utils/
│       ├── errors.py       # Handlers Flask para 400/404/422/500
│       └── validators.py   # Funções de validação de entrada (telefone, mes, campos obrigatórios)
│
├── tests/
│   ├── test_usuarios.py
│   ├── test_comprovantes.py
│   └── test_agendamentos.py
│
├── Dockerfile
├── docker-compose.yml  # ambiente de dev local (a criar — ver seção abaixo)
├── .env.example
└── requirements.txt
```

### Regra de responsabilidade única

| Camada | Pode fazer | Não pode fazer |
|---|---|---|
| `routes/` | validar entrada, ler/escrever cache, chamar queries, formatar JSON | executar SQL diretamente |
| `queries/` | executar SQL via `conn`, retornar `dict` ou `list[dict]` | acessar cache, retornar Response |
| `cache.py` | armazenar e expirar valores por TTL | saber nada de SQL ou HTTP |

---

## Pré-requisitos

- Python 3.12
- Docker + Docker Compose (para o banco local)
- `psql` (opcional — para inspecionar o banco diretamente)

---

## Configuração do ambiente de desenvolvimento

### 1. Clone e crie o virtualenv

```bash
git clone <repo-url>
cd data-svc

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env.local
```

Edite `.env.local` com as credenciais do banco local:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/meire_dev
PORT=5001
FLASK_ENV=development
TZ=America/Sao_Paulo
```

> Para apontar para o Supabase de staging/produção, substitua `DATABASE_URL` pela connection string do painel do Supabase. **Nunca use produção para desenvolvimento.**

### 3. Crie o docker-compose.yml para o banco local

Crie o arquivo `docker-compose.yml` na raiz do projeto:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: meire_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/01_schema.sql
      - ./scripts/seed.sql:/docker-entrypoint-initdb.d/02_seed.sql

volumes:
  pg_data:
```

### 4. Crie os scripts de banco local

Crie a pasta `scripts/` e os dois arquivos abaixo.

**`scripts/init.sql`** — schema das tabelas (solicitar ao responsável técnico).

Remova extensões específicas do Supabase que não existem no Postgres puro:

```sql
-- Comente ou remova estas linhas do schema antes de usar localmente:
-- CREATE EXTENSION IF NOT EXISTS "pg_graphql";
-- CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";
-- CREATE EXTENSION IF NOT EXISTS "pgjwt";
-- CREATE EXTENSION IF NOT EXISTS "supabase_vault";

-- Mantenha apenas:
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Cole o restante do schema a seguir...
```

**`scripts/seed.sql`** — dados mínimos para testar os endpoints:

```sql
INSERT INTO public.usuarios (
  numero_telefone, nome, razao_social, estado_atual,
  interacao_previa, tipo_negocio, data_primeiro_contato, data_ultimo_contato)
VALUES
  ('5511900000001', 'Dev Teste', 'Negocio Teste Ltda', 'menu',
   true, 'servico', NOW(), CURRENT_DATE),
  ('5511900000002', 'Maria Onboarding', 'Maria Costura', 'menu',
   false, null, NOW(), CURRENT_DATE)
ON CONFLICT DO NOTHING;

INSERT INTO public.comprovantes (
  usuario_id, item, quantidade, valor_unitario, valor_total,
  operacao, data_venda, item_hash)
SELECT u.id, 'Consultoria', 1, 500.00, 500.00, 'venda',
       CURRENT_DATE - 5, md5('consultoria-' || u.id::text)
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';

INSERT INTO public.comprovantes (
  usuario_id, item, quantidade, valor_unitario, valor_total,
  operacao, data_compra, item_hash)
SELECT u.id, 'Aluguel escritório', 1, 800.00, 800.00, 'gasto',
       CURRENT_DATE - 10, md5('aluguel-' || u.id::text)
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';

INSERT INTO public.agendamentos (
  usuario_id, nome_compromisso, data_compromisso,
  hora_compromisso, status, data_criacao, data_modificacao)
SELECT u.id, 'Reunião com cliente', CURRENT_DATE + 2,
       '14:00'::time, 'confirmado', NOW(), NOW()
FROM public.usuarios u WHERE u.numero_telefone = '5511900000001';
```

### 5. Suba o banco local

```bash
docker compose up db -d
```

O PostgreSQL executa `init.sql` e `seed.sql` automaticamente na **primeira** inicialização.

Aguarde ~5 segundos e verifique:

```bash
docker compose logs db
# deve terminar com: database system is ready to accept connections
```

---

## Rodando o servidor de desenvolvimento

Com o banco rodando e o `.env.local` configurado:

```bash
# Carrega as variáveis de ambiente e sobe o Flask em modo debug
export $(cat .env.local | xargs) && flask --app src/app run --port 5001 --debug
```

O servidor recarrega automaticamente a cada alteração de arquivo.

### Verificar que está funcionando

```bash
# Health check (a implementar no dia 2 do plano)
curl http://localhost:5001/health

# Buscar usuário do seed
curl "http://localhost:5001/usuarios?telefone=5511900000001"
```

---

## Rodando os testes

```bash
# Todos os testes
pytest

# Com output detalhado
pytest -v

# Apenas um módulo
pytest tests/test_usuarios.py -v
```

> Os testes estão como stubs (`pass`) — a suite só roda sem erros após as implementações.

---

## Cache

Implementado com `cachetools.TTLCache` — dict Python com expiração automática, sem Redis, sem infraestrutura extra.

| Rota | TTL | Chave | Invalidado por |
|---|---|---|---|
| `GET /usuarios?telefone=` | 60 s | `usuario:{telefone}` | `PUT /usuarios/<id>` |
| `GET /usuarios/<id>/saldo` | 300 s | `saldo:{id}:{mes}` | `POST /comprovantes` |
| `GET /usuarios/<id>/comprovantes` | 300 s | `comprovantes:{id}:{mes}:{modo}` | `POST /comprovantes` |
| `GET /usuarios/<id>/agendamentos` | 120 s | `agendamentos:{id}:{semana}` | `POST/PUT /agendamentos` |
| `GET /usuarios/<id>/listas` | 300 s | `listas:{id}` | `POST/DELETE /itens` |
| `GET .../listas/<id>/itens` | 300 s | `itens_lista:{id}` | `POST/DELETE /itens` |

---

## Resetar o banco local

```bash
# Apaga o volume e recria do zero com schema + seed
docker compose down -v
docker compose up db -d
```

---

## Build e execução via Docker

```bash
# Build da imagem
docker build -t data-svc .

# Executar apontando para o banco local
docker run --rm \
  -e DATABASE_URL=postgresql://postgres:postgres@host.docker.internal:5432/meire_dev \
  -p 5001:5000 \
  data-svc
```

> Em produção o deploy é feito pelo responsável técnico via Easypanel no VPS Hostinger.
