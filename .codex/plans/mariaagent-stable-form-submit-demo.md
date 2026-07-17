Complexidade: Simples

# Plano: estabilizar envio do front para demo

- [x] Trocar envio AJAX por submit tradicional com loading visual.
  - Validacao: o formulario deve postar em `/chat` e renderizar a resposta no HTML.
- [x] Evitar dependencia do MinIO no fluxo web `/chat`.
  - Validacao: `/chat` nao deve chamar reindex automatico antes de responder.
- [x] Rodar validacoes locais e publicar hotfix.
  - Validacao: `python -m compileall src`.
