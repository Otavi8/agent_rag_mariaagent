# Harness Reviewer

Use este checklist antes de publicar alteracoes relevantes:

- O WhatsApp ainda usa `FastAPI` + `/webhooks/evolution`.
- O chat web Flask e aditivo e nao substitui a API.
- `QDRANT_URL` aponta para o servico `qdrant` no Compose.
- `reindex` foi documentado quando o indice vetorial mudou.
- Langfuse continua opcional sem quebrar startup.
- `/metrics` existe na API e no web.
- `.env.example` nao contem secrets reais.
- `docker compose config` passa.
- Comandos de VPS usam `cd /opt/mariaagent`.
