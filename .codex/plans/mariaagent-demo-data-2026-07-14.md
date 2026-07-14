Complexidade: Medio

# Plano: dados demonstrativos ate 14/07/2026

- [x] Mapear schema/seeds/renderizacao atuais para definir os pontos de alteracao com baixo risco.
  - Validacao: confirmar arquivos e funcoes impactados antes de editar.
- [x] Criar as 7 novas tabelas comerciais no PostgreSQL e seus indices.
  - Validacao: compilar `database.py` sem erros de sintaxe.
- [x] Inserir ao menos 3 meses de dados, encerrando em 14/07/2026, para as tabelas novas e alinhar dados existentes ao mesmo periodo.
  - Validacao: validar contagens esperadas e datas finais nas estruturas de seed.
- [x] Atualizar renderizacao RAG, prompt e `SOURCE_TABLES` para que o agente enxergue as novas tabelas.
  - Validacao: compilar `documents.py` e `prompts.py`.
- [x] Atualizar documentacao com as novas tabelas e comandos de reindex/deploy na VPS.
  - Validacao: revisar trechos alterados e garantir comando de `reindex`.
- [x] Rodar validacoes locais possiveis e registrar limitações de runtime local.
  - Validacao: `python -m compileall src`, validacoes YAML/JSON se aplicavel, e `git diff --check`.
