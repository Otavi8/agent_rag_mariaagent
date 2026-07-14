Complexidade: Simples

# Plano: corrigir build Docker por template duplicado

- [x] Remover inclusao forcada duplicada dos templates no `pyproject.toml`.
  - Validacao: `python -m pip install -e .` ou build de metadata sem erro de template duplicado.
- [ ] Rodar validacoes locais rapidas e publicar o hotfix.
  - Validacao: commit e push para `origin/main`.
