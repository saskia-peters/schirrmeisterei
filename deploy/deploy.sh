#!/usr/bin/env bash
# TicketSystem – one-command deployment script
#
# Prerequisites: podman (or docker) + podman-compose (or docker compose)
#
# What this script does:
#   1. Generates a .env file with random secrets (first run only)
#   2. Pulls the latest container images
#   3. Starts the full stack (database + backend + frontend)
#
# The backend automatically runs database migrations on startup.
#
# Usage:
#   ./deploy.sh              Start the stack (generates .env on first run)
#   ./deploy.sh stop         Stop the stack
#   ./deploy.sh update       Pull latest images and restart
#   ./deploy.sh logs         Tail logs
#   ./deploy.sh status       Show container status

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Detect container runtime ─────────────────────────────────────────────────

if command -v podman &>/dev/null; then
    RUNTIME="podman"
    if command -v podman-compose &>/dev/null; then
        COMPOSE="podman-compose"
    elif podman compose version &>/dev/null 2>&1; then
        COMPOSE="podman compose"
    else
        echo "Error: podman-compose is required. Install it with: pip install podman-compose"
        exit 1
    fi
elif command -v docker &>/dev/null; then
    RUNTIME="docker"
    COMPOSE="docker compose"
else
    echo "Error: podman or docker is required."
    exit 1
fi

echo "Using: $RUNTIME ($COMPOSE)"

# ── Helper: generate random string ───────────────────────────────────────────

random_string() {
    python3 -c "import secrets; print(secrets.token_urlsafe(48))" 2>/dev/null \
        || openssl rand -base64 48 | tr -d '/+=' | head -c 64
}

# ── Generate .env on first run ────────────────────────────────────────────────

generate_env() {
    if [ -f .env ]; then
        echo ".env already exists – skipping generation."
        return
    fi

    echo "Generating .env with random secrets..."
    cat > .env <<EOF
# TicketSystem configuration – generated $(date -Iseconds)
# Edit these values as needed, then restart with: ./deploy.sh

# Database
POSTGRES_USER=ticketsystem
POSTGRES_PASSWORD=$(random_string)
POSTGRES_DB=ticketsystem

# Application secret (used for JWT signing)
SECRET_KEY=$(random_string)

# Ports exposed on the host
FRONTEND_PORT=8080
BACKEND_PORT=8000

# CORS allowed origins (JSON array)
ALLOWED_ORIGINS=["http://localhost:8080"]

# Max file upload size in MB
MAX_UPLOAD_SIZE_MB=10

# Image version tag (default: latest)
# TICKETSYSTEM_VERSION=latest
EOF
    echo "Created .env – review it before first start if needed."
}

# ── Commands ──────────────────────────────────────────────────────────────────

cmd_start() {
    generate_env
    echo "Pulling latest images..."
    $COMPOSE pull
    echo "Starting TicketSystem..."
    $COMPOSE up -d
    echo ""
    echo "TicketSystem is starting up."
    echo "  Frontend: http://localhost:$(grep -oP 'FRONTEND_PORT=\K.*' .env || echo 8080)"
    echo "  Backend:  http://localhost:$(grep -oP 'BACKEND_PORT=\K.*' .env || echo 8000)"
    echo ""
    echo "Default login: admin@example.com / admin  (change on first login)"
    echo "Run './deploy.sh logs' to follow startup progress."
}

cmd_stop() {
    echo "Stopping TicketSystem..."
    $COMPOSE down
}

cmd_update() {
    echo "Pulling latest images..."
    $COMPOSE pull
    echo "Restarting with new images..."
    $COMPOSE up -d
    echo "Update complete."
}

cmd_logs() {
    $COMPOSE logs -f
}

cmd_status() {
    $COMPOSE ps
}

# ── Main ──────────────────────────────────────────────────────────────────────

case "${1:-start}" in
    start)  cmd_start  ;;
    stop)   cmd_stop   ;;
    update) cmd_update ;;
    logs)   cmd_logs   ;;
    status) cmd_status ;;
    *)
        echo "Usage: $0 {start|stop|update|logs|status}"
        exit 1
        ;;
esac
