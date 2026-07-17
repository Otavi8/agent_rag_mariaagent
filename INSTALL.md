# Install na VPS Linux

Este guia assume uma VPS `Ubuntu` ou `Debian` limpa, com acesso SSH e dominio apontando para o IP do servidor.

## 1. Preparar DNS

Crie estes registros DNS apontando para a VPS:

- `maria.seudominio.com`
- `chat.seudominio.com`
- `evolution.seudominio.com`
- `minio.seudominio.com`
- `grafana.seudominio.com`
- `prometheus.seudominio.com`
- `traefik.seudominio.com`

Sem isso, o `Traefik` nao consegue emitir certificados TLS com `Let's Encrypt`.

## 2. Entrar na VPS

Conecte por SSH:

```bash
ssh root@IP_DA_VPS
```

Se quiser validar o sistema:

```bash
cat /etc/os-release
uname -m
```

## 3. Instalar o minimo para clonar o projeto

```bash
apt-get update
apt-get install -y ca-certificates curl git
```

## 4. Clonar o projeto

Escolha a pasta de deploy e clone:

```bash
mkdir -p /opt
cd /opt
git clone <URL_DO_REPOSITORIO> mariaagent
cd mariaagent
```

## 5. Instalar Docker, Compose e firewall

Rode o script de bootstrap do projeto:

```bash
chmod +x scripts/bootstrap-vps-debian-ubuntu.sh
./scripts/bootstrap-vps-debian-ubuntu.sh
```

Se o SSH da VPS usa outra porta, rode assim:

```bash
export SSH_PORT=2222
./scripts/bootstrap-vps-debian-ubuntu.sh
```

Esse script instala:

- `ufw`
- `docker-ce`
- `docker-ce-cli`
- `containerd.io`
- `docker-buildx-plugin`
- `docker-compose-plugin`

Tambem:

- habilita o servico do Docker
- abre `OpenSSH`, `80/tcp` e `443/tcp` no firewall

## 6. Criar o `.env`

```bash
cp .env.example .env
```

Edite:

```bash
nano .env
```

Troque pelo menos:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=uma-senha-forte
DATABASE_URL=postgresql://postgres:uma-senha-forte@postgres:5432/maria_agent

LLM_PROVIDER=openai
LLM_MODEL=gpt-4.1-mini
OPENAI_API_KEY=sua-chave-openai

EVOLUTION_API_KEY=sua-chave-segura-do-evolution
EVOLUTION_INSTANCE_NAME=maria-whatsapp
EVOLUTION_INTERNAL_WEBHOOK_URL=http://app:8000/webhooks/evolution

QDRANT_URL=http://qdrant:6333

MINIO_ENABLED=true
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=mariaagent
MINIO_SECRET_KEY=uma-senha-forte-minio
MINIO_RULES_BUCKET=maria-rules
MINIO_RULES_PREFIX=rules/

LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=sua-public-key-langfuse
LANGFUSE_SECRET_KEY=sua-secret-key-langfuse
LANGFUSE_HOST=https://cloud.langfuse.com

TRAEFIK_ACME_EMAIL=admin@seudominio.com
TRAEFIK_DASHBOARD_HOST=traefik.seudominio.com
TRAEFIK_APP_HOST=maria.seudominio.com
TRAEFIK_WEB_HOST=chat.seudominio.com
TRAEFIK_EVOLUTION_HOST=evolution.seudominio.com
TRAEFIK_MINIO_HOST=minio.seudominio.com
TRAEFIK_GRAFANA_HOST=grafana.seudominio.com
TRAEFIK_PROMETHEUS_HOST=prometheus.seudominio.com
TRAEFIK_BASIC_AUTH_USERS=admin:gere-seu-hash-aqui
GRAFANA_ADMIN_PASSWORD=troque-esta-senha
```

## 7. Gerar o hash do Basic Auth do Traefik

Instale o utilitario:

```bash
apt-get update
apt-get install -y apache2-utils
```

Gere o hash:

```bash
htpasswd -nbB admin 'SUA-SENHA-FORTE'
```

Copie a saida e coloque em `TRAEFIK_BASIC_AUTH_USERS`.

## 8. Subir a stack

```bash
docker compose up -d --build
```

Verifique:

```bash
docker compose ps
docker compose logs -f traefik
docker compose logs -f app
docker compose logs -f web
docker compose logs -f evolution-go
docker compose logs -f postgres
docker compose logs -f qdrant
docker compose logs -f prometheus
docker compose logs -f grafana
```

## 9. Inicializar os dados

Se for ambiente novo:

```bash
docker compose exec app python -m maria_rag_agent.cli init-db
docker compose exec app python -m maria_rag_agent.cli seed-db
docker compose exec app python -m maria_rag_agent.cli ensure-rules-bucket
docker compose exec app python -m maria_rag_agent.cli reindex
```

O `seed-db` recria os dados demonstrativos de `17/04/2026` ate `17/07/2026`, incluindo vendas, estoque, compras, entregas, pedidos de clientes, metas, precos e equipe. O `ensure-rules-bucket` cria o bucket de regras no MinIO. O `reindex` recria a colecao no Qdrant com base nos dados do PostgreSQL e nas regras `.md`/`.txt` encontradas no MinIO.

Se a VPS ja tiver uma versao antiga da base, rode novamente:

```bash
docker compose exec app python -m maria_rag_agent.cli seed-db
docker compose exec app python -m maria_rag_agent.cli ensure-rules-bucket
docker compose exec app python -m maria_rag_agent.cli reindex
```

Para inserir regras, acesse o console do MinIO pelo host configurado em `TRAEFIK_MINIO_HOST`, crie ou abra o bucket `maria-rules`, envie arquivos `.md` ou `.txt` dentro da pasta `rules/`, e rode:

```bash
docker compose exec app python -m maria_rag_agent.cli list-rules
docker compose exec app python -m maria_rag_agent.cli reindex
```

Se for migrar do `SQLite` legado:

1. copie o arquivo `maria_agent.db` para `./data/`
2. rode:

```bash
docker compose exec app python -m maria_rag_agent.cli migrate-sqlite --sqlite-path /app/data/maria_agent.db --replace-existing
docker compose exec app python -m maria_rag_agent.cli reindex
```

## 10. Validar a API

Health check:

```bash
curl -u admin:SUA-SENHA-FORTE https://maria.seudominio.com/health
```

Chat web:

```bash
curl -u admin:SUA-SENHA-FORTE https://chat.seudominio.com/
```

Grafana:

```text
https://grafana.seudominio.com
```

Pergunta de teste:

```bash
curl -X POST https://maria.seudominio.com/api/ask \
  -u admin:SUA-SENHA-FORTE \
  -H "Content-Type: application/json" \
  -d '{"question":"Quais produtos estao abaixo do ponto de reposicao?","user_id":"teste-vps"}'
```

## 11. Criar a instancia do WhatsApp

Criar:

```bash
curl -X POST https://maria.seudominio.com/api/evolution/instances/create \
  -u admin:SUA-SENHA-FORTE \
  -H "Content-Type: application/json" \
  -d '{"instance_name":"maria-whatsapp"}'
```

Conectar:

```bash
curl -X POST https://maria.seudominio.com/api/evolution/instances/connect \
  -u admin:SUA-SENHA-FORTE \
  -H "Content-Type: application/json" \
  -d '{"subscribe":["MESSAGE","CONNECTION","QRCODE"],"immediate":true}'
```

Consultar estado:

```bash
curl -u admin:SUA-SENHA-FORTE https://maria.seudominio.com/api/evolution/instances
```

## 12. Comandos uteis

Reiniciar stack:

```bash
docker compose down
docker compose up -d --build
```

Ver containers:

```bash
docker compose ps
```

Entrar no container da app:

```bash
docker compose exec app sh
```

Ver configuracao:

```bash
docker compose exec app python -m maria_rag_agent.cli show-config
```

## 13. Problemas comuns

Certificado nao sai:

- confirme DNS apontando para a VPS
- confirme portas `80` e `443` liberadas
- veja `docker compose logs -f traefik`

App nao sobe:

- confirme `.env`
- veja `docker compose logs -f app`

PostgreSQL falha:

- veja `docker compose logs -f postgres`
- se estiver reaproveitando volume antigo, o script de criacao de bancos pode nao rodar de novo

Evolution nao responde:

- confira `EVOLUTION_API_KEY`
- confira se a instancia foi criada e conectada
- veja `docker compose logs -f evolution-go`
