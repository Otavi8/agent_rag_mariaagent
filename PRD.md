# PRD - Maria RAG Agent Replicavel

## Objetivo

Documentar um modelo replicavel de agent RAG com banco relacional, banco vetorial, API HTTP e integracao com WhatsApp, para que outro time consiga subir uma instancia equivalente com o proprio dominio de negocio.

## Resumo executivo

Este projeto entrega uma base de agent operacional com:

- `PostgreSQL` como fonte de verdade
- `Qdrant` para recuperacao semantica
- `MinIO` para regras operacionais em arquivos
- `LangChain` para coordenar tools e resposta
- `FastAPI` para API e webhook
- `Flask` para chat web com visibilidade das consultas do agente
- `Evolution Go` para receber e responder mensagens do WhatsApp
- `Traefik` para publicar tudo com HTTPS em um unico `docker-compose.yml`
- `Langfuse`, `Prometheus` e `Grafana` para tracing e monitoramento

O desenho foi pensado para perguntas operacionais que misturam:

- fatos exatos, datas, totais e filtros
- contexto textual, explicacoes e apoio a decisao
- continuidade de conversa com controle de tokens

## Problema que o modelo resolve

Times operacionais normalmente precisam consultar dados estruturados e explicar o contexto desses dados no mesmo fluxo de atendimento. Um RAG puramente vetorial nao e suficiente para responder com exatidao numerica. Um fluxo puramente SQL nao cobre bem perguntas abertas.

Este modelo resolve isso com uma arquitetura hibrida:

- SQL para respostas exatas
- RAG vetorial para contexto e linguagem natural
- memoria persistente para nao reenviar a conversa inteira
- webhook para entrada por WhatsApp

## Perfil de uso

Personas principais:

- gerente de loja
- supervisor operacional
- time interno que quer embutir perguntas em outro sistema
- equipe que quer um canal de WhatsApp para atendimento interno

## Objetivos do produto

- responder perguntas operacionais em linguagem natural
- manter rastreabilidade da origem dos dados
- suportar multiplos usuarios e conversas
- reduzir consumo de tokens com resumo de historico
- permitir deploy simples em VPS Linux com Docker
- permitir adaptacao para outros dominios sem reescrever a arquitetura inteira

## Fora de escopo

- painel administrativo completo
- autenticacao corporativa SSO
- multi-tenant forte com isolamento por banco por cliente
- fila de jobs distribuida
- observabilidade enterprise alem de tracing Langfuse e dashboards Grafana basicos

## Requisitos funcionais

### RF-01. Banco transacional

O sistema deve armazenar os dados operacionais em `PostgreSQL`.

Base demonstrativa atual:

- periodo de dados: `14/04/2026` ate `14/07/2026`
- data de referencia para perguntas de demo como "hoje": `14/07/2026`
- tabelas de negocio: `product_catalog`, `sales`, `employees`, `absenteeism_events`, `purchase_orders`, `inventory_movements`, `daily_stock_snapshot`, `customer_orders`, `sales_targets`, `supplier_deliveries` e `product_price_history`

### RF-02. Indexacao vetorial

O sistema deve ler tabelas configuradas, converter registros em `Document`, quebrar em chunks e persistir vetores no `Qdrant`.

O sistema tambem deve ler regras operacionais no MinIO em arquivos `.md` ou `.txt`, converter cada arquivo em `Document` e indexar esse contexto junto com os dados estruturados.

### RF-03. Agent hibrido

O agent deve conseguir responder usando:

- busca vetorial
- SQL somente leitura

### RF-04. API HTTP

O sistema deve expor endpoints para:

- health check
- pergunta direta
- operacao da integracao com `Evolution Go`

### RF-05. WhatsApp

O sistema deve receber eventos do `Evolution Go` e enviar respostas ao numero de origem.

### RF-06. Memoria

O sistema deve salvar:

- conversas
- mensagens
- resumos
- memorias duraveis por usuario

### RF-07. Migracao de legado

O sistema deve suportar migracao do banco legado `SQLite` para `PostgreSQL`.

### RF-08. Deploy unificado

O sistema deve subir com um unico `docker-compose.yml`, incluindo app, banco, proxy e camada de WhatsApp.

## Requisitos nao funcionais

### RNF-01. Seguranca minima

- SQL deve ser somente leitura
- variaveis sensiveis devem sair do codigo e ir para `.env`
- `Traefik` deve proteger a borda com TLS
- endpoints publicados devem aceitar protecao por `basic auth`

### RNF-02. Replicabilidade

- outro time deve conseguir subir a stack com base em `.env.example`, `README.md` e este `PRD.md`
- a mudanca de dominio deve ficar concentrada em poucos arquivos

### RNF-03. Simplicidade operacional

- stack orientada a VPS unica
- sem dependencia obrigatoria de Kubernetes
- comandos claros para bootstrap e manutencao

### RNF-04. Persistencia

- `PostgreSQL` deve persistir em volume Docker
- `Qdrant` deve persistir em volume Docker

## Arquitetura alvo

```text
Usuario
  -> WhatsApp
  -> Evolution Go
  -> Webhook FastAPI
  -> Agent LangChain
     -> SQL read only no PostgreSQL
     -> semantic search no Qdrant
  -> resposta

Usuario tecnico
  -> CLI, API HTTP ou chat Flask
  -> mesmo agent e mesmas tools
```

## Componentes da solucao

### 1. PostgreSQL

Responsabilidades:

- armazenar dados de negocio
- armazenar memoria de conversa
- armazenar estado de instancia do WhatsApp

### 2. Qdrant

Responsabilidades:

- armazenar embeddings
- recuperar contexto semantico

### 3. MinIO

Responsabilidades:

- armazenar regras operacionais escritas por usuarios
- manter arquivos `.md` e `.txt` no bucket `maria-rules`
- disponibilizar as regras para o `reindex`

### 4. LangChain agent

Responsabilidades:

- interpretar a pergunta
- decidir entre SQL e busca vetorial
- montar resposta final

### 4. FastAPI

Responsabilidades:

- expor endpoints HTTP
- receber webhook do WhatsApp
- acionar o agent

### 4.1 Flask web

Responsabilidades:

- oferecer uma interface de chat para usuarios que nao estao no WhatsApp
- exibir a resposta e as ferramentas usadas pelo agente
- mostrar a consulta SQL executada quando a tool `sql_read_only_query` for usada

### 5. Evolution Go

Responsabilidades:

- conectar o WhatsApp
- encaminhar eventos
- enviar mensagens de resposta

### 6. Traefik

Responsabilidades:

- receber trafego externo
- emitir certificados TLS
- rotear por host

## Fluxos principais

### Fluxo A. Pergunta por CLI ou API

1. usuario envia pergunta
2. sistema carrega configuracao
3. sistema garante indice vetorial disponivel
4. agent consulta memoria relevante
5. agent usa SQL, RAG, ou ambos
6. sistema devolve resposta

### Fluxo B. Pergunta por WhatsApp

1. mensagem chega ao WhatsApp
2. `Evolution Go` envia webhook para a app
3. app valida o evento
4. app ignora grupos ou newsletters quando configurado
5. agent responde
6. app envia texto de volta via `Evolution Go`

### Fluxo C. Indexacao

1. sistema le `SOURCE_TABLES`
2. transforma registros em documentos
3. quebra em chunks
4. gera embeddings
5. persiste no `Qdrant`

### Fluxo D. Migracao do legado

1. operador fornece o caminho do `SQLite`
2. CLI cria o schema em `PostgreSQL`
3. CLI copia dados de tabelas compativeis
4. operador roda `reindex`

## Arquivos que devem ser adaptados em um novo dominio

Arquivos obrigatorios:

- `src/maria_rag_agent/database.py`
- `src/maria_rag_agent/documents.py`
- `src/maria_rag_agent/prompts.py`
- `.env.example`
- `README.md`

Arquivos opcionais:

- `src/maria_rag_agent/tools.py`
- `src/maria_rag_agent/guardrails.py`
- `docker-compose.yml`

## Parametros minimos para replicacao

Infraestrutura:

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

LLM:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OPENAI_API_KEY` ou equivalente

WhatsApp:

- `EVOLUTION_ENABLED`
- `EVOLUTION_BASE_URL`
- `EVOLUTION_API_KEY`
- `EVOLUTION_INSTANCE_NAME`

Borda:

- `TRAEFIK_ACME_EMAIL`
- `TRAEFIK_APP_HOST`
- `TRAEFIK_EVOLUTION_HOST`
- `TRAEFIK_BASIC_AUTH_USERS`

## Passo a passo para outro time replicar

### Etapa 1. Clonar e instalar

```bash
git clone <repo>
cd mariaagent
cp .env.example .env
```

### Etapa 2. Configurar variaveis

Preencher:

- banco
- modelo
- hosts do Traefik
- credenciais do Evolution Go

### Etapa 3. Subir a stack

```bash
docker compose up -d --build
```

### Etapa 4. Inicializar dados

Se for ambiente novo:

```bash
docker compose exec app python -m maria_rag_agent.cli init-db
docker compose exec app python -m maria_rag_agent.cli seed-db
docker compose exec app python -m maria_rag_agent.cli ensure-rules-bucket
docker compose exec app python -m maria_rag_agent.cli reindex
```

O `seed-db` carrega a base demonstrativa de 3 meses ate `14/07/2026`. O `ensure-rules-bucket` prepara o bucket de regras no MinIO. O `reindex` deve ser executado depois para enviar as tabelas configuradas em `SOURCE_TABLES` e os arquivos de regra para o Qdrant.

Se vier de `SQLite`:

```bash
docker compose exec app python -m maria_rag_agent.cli migrate-sqlite --sqlite-path /app/data/maria_agent.db --replace-existing
docker compose exec app python -m maria_rag_agent.cli reindex
```

### Etapa 5. Validar

Checklist minimo:

- `GET /health` responde
- `POST /api/ask` responde
- indice vetorial foi criado
- instancia do WhatsApp foi criada
- webhook recebe `MESSAGE`

## Criterios de aceitacao

O modelo sera considerado replicado com sucesso quando:

- a stack subir com um unico compose
- o `PostgreSQL` estiver operacional
- o agent responder por CLI
- o agent responder por API HTTP
- o `Evolution Go` conseguir entregar uma mensagem ao webhook
- a app conseguir responder de volta ao WhatsApp
- a memoria por conversa estiver sendo persistida

## Riscos e pontos de atencao

- schema do novo dominio mal adaptado quebra a qualidade do RAG
- renderizacao ruim em `documents.py` empobrece os embeddings
- sem `reindex`, o agent pode responder com contexto vazio
- expor a stack sem revisar `basic auth`, dominio e TLS aumenta risco operacional
- vazar `.env` compromete API keys e dados do ambiente

## Evolucoes recomendadas

- avaliacao automatica de respostas
- backups agendados do `PostgreSQL`
- monitoramento e logs centralizados
- autenticacao mais forte para a API
- filtros por loja, filial ou tenant
- pipeline de importacao de dados reais

## Decisao de produto

Este projeto deve ser tratado como um template operacional replicavel, nao apenas como um experimento local. Toda nova instancia deve preservar a arquitetura base e trocar apenas:

- dominio de negocio
- schema e seeds
- prompt
- configuracoes de deploy
