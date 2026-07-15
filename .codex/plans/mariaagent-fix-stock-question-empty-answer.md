Complexidade: Simples

# Plano: corrigir pergunta de estoque sem resposta

- [x] Confirmar onde nasce a mensagem generica de resposta vazia.
  - Validacao: localizar fallback no front e retorno JSON da API.
- [x] Melhorar a API/front para nao mascarar resposta ausente.
  - Validacao: resposta vazia deve virar erro claro em JSON.
- [x] Adicionar fallback SQL deterministico para pergunta geral de estoque.
  - Validacao: pergunta "gostaria de saber quais produtos temos em estoque?" deve retornar produtos com estoque.
- [x] Rodar validacoes locais e publicar para VPS.
  - Validacao: `python -m compileall src`.
