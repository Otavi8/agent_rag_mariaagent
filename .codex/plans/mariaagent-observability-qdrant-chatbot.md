Complexidade: Complexo

- [x] Preservar o estado atual e mapear o runtime existente.
  - Validacao: confirmar branch/remoto, listar mudancas locais ja existentes e identificar pontos de entrada da API, WhatsApp, RAG e vector store.
- [x] Migrar o vector store de ChromaDB para Qdrant sem mudar a base relacional.
  - Validacao local: imports e `python -m compileall src`; validacao runtime de `reindex` fica para VPS com Docker/Qdrant.
- [x] Adicionar observabilidade com Langfuse de forma opcional.
  - Validacao: imports reais passaram; sem chaves, o handler retorna lista vazia e a aplicacao continua rodando.
- [x] Adicionar Prometheus + Grafana no Docker Compose.
  - Validacao local: YAML/JSON de observabilidade carregaram; `docker compose config` fica para VPS porque Docker nao esta disponivel localmente.
- [x] Criar aplicacao Flask de chat web sem remover o WhatsApp.
  - Validacao: `maria_rag_agent.web` importou e a app Flask carregou.
- [x] Adicionar estrutura de harness compatibilizada com este projeto.
  - Validacao: arquivos `CONTEXT.md`, `CODEX.md`, `AGENTS.md` e reviewer adicionados sem alterar entrypoints.
- [x] Atualizar `.env.example`, README/INSTALL e instrucoes de deploy VPS.
  - Validacao: variaveis novas e comandos de rebuild/reindex documentados.
- [x] Rodar validacoes locais possiveis.
  - Validacao: `python -m compileall src`, imports reais, YAML/JSON e `python -m maria_rag_agent.cli show-config`.

Observacao: a validacao final de Qdrant, Compose e Grafana deve ser feita na VPS com `docker compose up -d --build` e `reindex`.
