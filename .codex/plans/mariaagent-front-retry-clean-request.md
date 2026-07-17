Complexidade: Simples

# Plano: fallback limpo no front do chat

- [x] Adicionar segunda tentativa limpa quando `/api/chat` vier vazio ou erro.
  - Validacao: o front deve repetir a pergunta sem `conversation_id`/`store_id`, igual ao curl que funcionou.
- [x] Rodar validacoes locais e publicar hotfix.
  - Validacao: `python -m compileall src`.
