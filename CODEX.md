# Guia Codex - Maria RAG Agent

## Padrao de trabalho

- Leia `CONTEXT.md`, `README.md`, `INSTALL.md` e o arquivo de plano em `.codex/plans/` antes de alteracoes grandes.
- Preserve o fluxo de WhatsApp existente.
- Prefira evolucoes incrementais sobre refatoracoes amplas.
- Use `.env.example` apenas com placeholders.
- Antes de publicar, rode busca por segredos.

## Pontos centrais do codigo

- `src/maria_rag_agent/agent.py`: criacao e execucao do agente.
- `src/maria_rag_agent/tools.py`: tools `semantic_search` e `sql_read_only_query`.
- `src/maria_rag_agent/vectorstore.py`: Qdrant e reindex.
- `src/maria_rag_agent/api.py`: FastAPI, WhatsApp e metricas.
- `src/maria_rag_agent/web.py`: chat Flask.
- `src/maria_rag_agent/observability.py`: Langfuse, Prometheus e rastreamento de tools.
- `src/maria_rag_agent/database.py`: schema PostgreSQL e seeds.

## Validacoes recomendadas

```bash
python -m compileall src
python -m maria_rag_agent.cli show-config
docker compose config
```

Em maquina com Docker/Qdrant:

```bash
docker compose up -d --build
docker compose exec app python -m maria_rag_agent.cli reindex
docker compose exec app python -m maria_rag_agent.cli ask "quantas vendas tivemos ?"
```
