Complexidade: Simples

# Plano: atualizar demo para 17/07/2026 e corrigir MinIO

- [x] Atualizar dados demonstrativos e prompt para considerar 17/07/2026 como hoje.
  - Validacao: localizar e substituir referencias de 14/07/2026 no seed e prompt.
- [x] Ajustar publicacao do MinIO para console e API.
  - Validacao: Compose deve publicar 9000 e 9001 e aceitar URLs publicas por `.env`.
- [x] Atualizar documentacao de deploy/demo.
  - Validacao: docs devem citar periodo ate 17/07/2026 e comandos `seed-db`/`reindex`.
- [x] Rodar validacoes locais e publicar no GitHub.
  - Validacao: `python -m compileall src` e varredura basica de secrets.
