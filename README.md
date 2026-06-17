# Maria RAG Agent

Assistente de estudo com arquitetura pronta para producao leve, pensada para responder perguntas operacionais sobre uma loja de autopecas por CLI, API HTTP e WhatsApp.

## O que este projeto entrega

- `PostgreSQL` como banco transacional principal
- `Chroma` como banco vetorial local
- `LangChain` para orquestracao do agent e das tools
- `FastAPI` para API e webhook
- `Evolution Go` para integracao com WhatsApp
- `Traefik` para borda HTTP/HTTPS no deploy com Docker
- memoria conversacional persistente por usuario e conversa

## Arquitetura em uma frase

Os dados operacionais ficam no `PostgreSQL`, sao indexados no `Chroma`, e a Maria responde usando um modelo hibrido que combina busca vetorial com consulta SQL somente leitura.

## Fluxo principal

1. O `PostgreSQL` guarda os dados da operacao.
2. O pipeline transforma linhas das tabelas em `Document`.
3. Os documentos sao quebrados em chunks e vetorizados no `Chroma`.
4. O agent decide entre `semantic_search` para contexto semantico e `sql_read_only_query` para dados exatos.
5. A resposta pode sair por CLI, API HTTP ou WhatsApp.
6. No WhatsApp, o `Evolution Go` recebe a mensagem e chama o webhook da Maria.
7. No deploy, o `Traefik` publica a stack com TLS e roteamento por host.

## Casos de uso

- responder perguntas sobre vendas, estoque e cobertura de equipe
- manter contexto entre conversas sem reenviar todo o historico
- expor o agent por API para outras integracoes
- operar um fluxo de atendimento por WhatsApp com uma stack unica em Docker

## Estrutura principal

```text
src/maria_rag_agent/
  agent.py
  api.py
  cli.py
  config.py
  database.py
  documents.py
  evolution.py
  guardrails.py
  memory.py
  migrations.py
  prompts.py
  tools.py
  vectorstore.py
docker/
data/
storage/
Dockerfile
docker-compose.yml
.env.example
PRD.md
```

## Comeco rapido local

### 1. Instalar dependencias

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

Opcional com `Ollama`:

```powershell
pip install -e .[ollama]
```

### 2. Criar o `.env`

```powershell
Copy-Item .env.example .env
```

Campos minimos para OpenAI:

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua-chave
```

Campos minimos para banco:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-this-password
DATABASE_URL=postgresql://postgres:change-this-password@localhost:5432/maria_agent
```

### 3. Inicializar o banco

```powershell
python -m maria_rag_agent.cli init-db
python -m maria_rag_agent.cli seed-db
python -m maria_rag_agent.cli reindex
```

### 4. Fazer a primeira pergunta

```powershell
python -m maria_rag_agent.cli ask "Quais produtos estao abaixo do ponto de reposicao?"
```

## Comandos principais

Criar schema:

```powershell
python -m maria_rag_agent.cli init-db
```

Popular dados de exemplo:

```powershell
python -m maria_rag_agent.cli seed-db
```

Migrar banco legado `SQLite` para `PostgreSQL`:

```powershell
python -m maria_rag_agent.cli migrate-sqlite --sqlite-path data/maria_agent.db
```

Sobrescrever dados existentes no `PostgreSQL`:

```powershell
python -m maria_rag_agent.cli migrate-sqlite --sqlite-path data/maria_agent.db --replace-existing
```

Reindexar o banco vetorial:

```powershell
python -m maria_rag_agent.cli reindex
```

Perguntar ao agent:

```powershell
python -m maria_rag_agent.cli ask "Quais categorias mais geraram caixa nesta semana?"
```

Continuar uma conversa:

```powershell
python -m maria_rag_agent.cli ask "Quem pode cobrir o vendas_balcao?" --conversation-id conv_demo_01 --user-id gerente_loja_01 --store-id loja_centro
```

Listar conversas:

```powershell
python -m maria_rag_agent.cli list-conversations --user-id gerente_loja_01
```

Listar memorias do usuario:

```powershell
python -m maria_rag_agent.cli list-user-memories gerente_loja_01 --store-id loja_centro
```

Subir a API local:

```powershell
python -m maria_rag_agent.api
```

## Endpoints principais

Health check:

```bash
curl http://localhost:8000/health
```

Pergunta via HTTP:

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"Quais produtos estao abaixo do ponto de reposicao?\",\"user_id\":\"teste-http\"}"
```

Criar instancia do WhatsApp:

```bash
curl -X POST http://localhost:8000/api/evolution/instances/create \
  -H "Content-Type: application/json" \
  -d "{\"instance_name\":\"maria-whatsapp\"}"
```

Conectar instancia:

```bash
curl -X POST http://localhost:8000/api/evolution/instances/connect \
  -H "Content-Type: application/json" \
  -d "{\"subscribe\":[\"MESSAGE\",\"CONNECTION\",\"QRCODE\"],\"immediate\":true}"
```

## Docker e VPS

O projeto inclui uma stack unica em [docker-compose.yml](docker-compose.yml) com:

- `traefik`
- `postgres`
- `app`
- `evolution-go`

Subir toda a stack:

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f traefik
docker compose logs -f app
docker compose logs -f evolution-go
docker compose logs -f postgres
```

Parar a stack:

```bash
docker compose down
```

Migrar o `SQLite` legado ja dentro da stack:

```bash
docker compose exec app python -m maria_rag_agent.cli migrate-sqlite --sqlite-path /app/data/maria_agent.db --replace-existing
docker compose exec app python -m maria_rag_agent.cli reindex
```

Esse fluxo funciona porque `./data` e montado em `/app/data` no container da app.

## Variaveis mais importantes

Banco e API:

- `DATABASE_URL`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `API_HOST`
- `API_PORT`

RAG:

- `SOURCE_TABLES`
- `CHUNK_SIZE`
- `CHUNK_OVERLAP`
- `SEARCH_K`
- `SEARCH_FETCH_K`
- `MAX_CONTEXT_CHARS`

Memoria:

- `ENABLE_CONVERSATION_MEMORY`
- `ENABLE_USER_MEMORY`
- `MEMORY_RECENT_MESSAGES`
- `MEMORY_SUMMARIZE_AFTER_MESSAGES`
- `USER_MEMORY_TOP_K`

WhatsApp:

- `EVOLUTION_ENABLED`
- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE_NAME`
- `EVOLUTION_SUBSCRIBE_EVENTS`
- `EVOLUTION_WEBHOOK_SECRET`

Traefik:

- `TRAEFIK_ACME_EMAIL`
- `TRAEFIK_DASHBOARD_HOST`
- `TRAEFIK_APP_HOST`
- `TRAEFIK_EVOLUTION_HOST`
- `TRAEFIK_BASIC_AUTH_USERS`

Veja os defaults em [.env.example](.env.example).

## Como replicar para outro negocio

1. Troque o schema e os seeds em `database.py`.
2. Ajuste os renderizadores em `documents.py`.
3. Reescreva o prompt do agent em `prompts.py`.
4. Atualize `SOURCE_TABLES` e os exemplos do `.env`.
5. Rode `init-db`, `seed-db` ou `migrate-sqlite`, e depois `reindex`.
6. Teste por CLI antes de expor por API ou WhatsApp.

## Arquivos de referencia

- [PRD.md](PRD.md): documento para replicacao do modelo por outros times
- [INSTALL.md](INSTALL.md): roteiro de instalacao em VPS Linux crua
- [.env.example](.env.example): configuracao base
- [docker-compose.yml](docker-compose.yml): stack unica da VPS
- [Dockerfile](Dockerfile): imagem da aplicacao

## Observacoes importantes

- o dominio atual de exemplo e autopecas, mas a arquitetura e generica
- o banco principal nao e mais `SQLite`; agora e `PostgreSQL`
- o `Chroma` continua local em `./storage`
- a chave real da OpenAI nunca deve ser commitada
- antes de publicar, revise `.env`, dominios, credenciais e hashes de `basic auth`
