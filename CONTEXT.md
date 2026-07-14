# Contexto Vivo - Maria RAG Agent

## Objetivo atual

Evoluir o Maria RAG Agent para uma demonstracao profissional com:

- WhatsApp via Evolution Go preservado.
- API FastAPI preservada.
- Chat web Flask para usuarios sem WhatsApp.
- Qdrant como banco vetorial padrao.
- Langfuse, Prometheus e Grafana para observabilidade.
- PostgreSQL como fonte de verdade e memoria conversacional.

## Decisoes importantes

- Nao reescrever o core no formato completo de outro template antes da apresentacao.
- Manter `ask_agent()` como ponto central de execucao do agente.
- Recriar o indice vetorial via `reindex`, usando PostgreSQL como fonte.
- Expor a consulta SQL usada pelo agente por meio do rastreamento das tools.
- Manter o container `python` de compatibilidade para `docker compose exec python cli.py ask "..."`.

## Stack atual

- Python 3.11
- LangChain Agents
- FastAPI
- Flask
- PostgreSQL
- Qdrant
- Evolution Go
- Traefik
- Langfuse
- Prometheus
- Grafana

## Comandos de validacao

```bash
python -m compileall src
docker compose config
docker compose up -d --build
docker compose exec app python -m maria_rag_agent.cli reindex
docker compose exec app python -m maria_rag_agent.cli ask "quantas vendas tivemos ?"
```

## Cuidados

- Nunca commitar `.env`, dados locais, chaves da OpenAI, Langfuse ou Evolution.
- Em VPS, rodar comandos a partir de `/opt/mariaagent`.
- Se `docker compose` ler `/root/.env`, usar `cd /opt/mariaagent` ou `--project-directory /opt/mariaagent`.
