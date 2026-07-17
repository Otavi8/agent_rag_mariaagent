Complexidade: Simples

# Plano: corrigir resposta vazia do agente

- [x] Corrigir extracao de resposta para buscar a ultima mensagem textual do assistente.
  - Validacao: mensagens finais vazias nao devem apagar uma resposta anterior valida.
- [x] Rodar validacoes locais e publicar hotfix.
  - Validacao: `python -m compileall src`.
