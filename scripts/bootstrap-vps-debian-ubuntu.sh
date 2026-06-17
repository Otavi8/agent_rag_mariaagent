#!/usr/bin/env bash

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Execute este script como root: sudo ./scripts/bootstrap-vps-debian-ubuntu.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

SSH_PORT="${SSH_PORT:-22}"

. /etc/os-release

case "${ID}" in
  ubuntu|debian)
    DOCKER_DISTRO="${ID}"
    DOCKER_CODENAME="${VERSION_CODENAME}"
    ;;
  *)
    echo "Distribuicao nao suportada por este script: ${ID}"
    echo "Use Ubuntu ou Debian, ou adapte manualmente o repositorio do Docker."
    exit 1
    ;;
esac

echo "[1/8] Atualizando pacotes base"
apt-get update
apt-get install -y ca-certificates curl git gnupg lsb-release ufw

echo "[2/8] Removendo pacotes Docker antigos, se existirem"
apt-get remove -y docker.io docker-doc docker-compose podman-docker containerd runc || true

echo "[3/8] Preparando keyrings do Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL "https://download.docker.com/linux/${DOCKER_DISTRO}/gpg" -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "[4/8] Configurando repositorio oficial do Docker"
cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/${DOCKER_DISTRO} ${DOCKER_CODENAME} stable
EOF

echo "[5/8] Instalando Docker Engine e Compose plugin"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "[6/8] Habilitando Docker"
systemctl enable docker
systemctl restart docker

echo "[7/8] Configurando firewall"
ufw allow "${SSH_PORT}/tcp"
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "[8/8] Validando instalacao"
docker --version
docker compose version
systemctl --no-pager --full status docker | sed -n '1,12p'

echo
echo "Bootstrap concluido."
echo "Proximo passo:"
echo "  1. git clone <repo> mariaagent"
echo "  2. cd mariaagent"
echo "  3. cp .env.example .env"
echo "  4. docker compose up -d --build"
