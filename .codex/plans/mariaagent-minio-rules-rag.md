Complexidade: Medio

# Plano: regras operacionais no MinIO

- [x] Mapear os pontos atuais de configuracao, compose e reindexacao.
  - Validacao: confirmar arquivos impactados antes de editar.
- [x] Adicionar dependencias e variaveis de configuracao para MinIO/regras.
  - Validacao: `python -m py_compile src/maria_rag_agent/config.py`.
- [x] Adicionar servico MinIO no Docker Compose com volume, healthcheck e variaveis.
  - Validacao: validar YAML do `docker-compose.yml`.
- [x] Criar loader de regras `.md`/`.txt` do MinIO como documentos LangChain.
  - Validacao: compilar o modulo novo e testar fallback quando MinIO esta desabilitado.
- [x] Integrar regras ao `reindex` e expor contadores no CLI.
  - Validacao: compilar `vectorstore.py` e checar retorno esperado sem MinIO ativo.
- [x] Atualizar prompt e documentacao com uso das regras e comandos de VPS.
  - Validacao: revisar mencoes de MinIO e `reindex`.
- [x] Rodar validacoes locais possiveis e checagem de secrets.
  - Validacao: `python -m compileall src`, YAML/JSON, `git diff --check` e secret scan.
