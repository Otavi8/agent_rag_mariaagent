# Instrucoes Para Agentes

## Regras principais

- Mantenha compatibilidade com o deploy Docker/VPS.
- Nao remova o fluxo WhatsApp/Evolution Go sem pedido explicito.
- Nao sobrescreva `.env`, `data/`, `storage/` ou volumes locais.
- Use Qdrant para busca vetorial; nao reintroduza Chroma.
- Quando mudar schema ou indexacao, documente o comando `reindex`.
- Toda nova rota externa deve ser considerada no Traefik e na documentacao.

## Observabilidade

- Langfuse deve continuar opcional.
- Prometheus deve expor metricas sem exigir secrets.
- A UI web deve mostrar as tools chamadas pelo agente, principalmente SQL.

## Antes de publicar

```bash
python -m compileall src
docker compose config
rg -n "sk-|OPENAI_API_KEY=sk-|LANGFUSE_SECRET_KEY=sk-|EVOLUTION_API_KEY=.*[A-Za-z0-9]{20,}" .
```
