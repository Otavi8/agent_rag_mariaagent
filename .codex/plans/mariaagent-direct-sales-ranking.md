Complexidade: Simples

# Plano: resposta direta para itens mais vendidos

- [x] Corrigir fallback de estoque que ainda ordenava por coluna inexistente.
  - Validacao: consulta deve usar `p.description`.
- [x] Adicionar resposta SQL deterministica para itens mais vendidos.
  - Validacao: pergunta "preciso de ajuda para saber quais itens sao os mais vendidos" deve acionar o caminho direto.
- [x] Rodar validacoes locais e publicar hotfix para VPS.
  - Validacao: `python -m compileall src`.
