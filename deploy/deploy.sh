#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Portfolio CMS - Server Setup & Deployment Script
# Run as root on a fresh Ubuntu 24.04 VPS
# Usage:
#   ./deploy.sh setup    - First-time server setup
#   ./deploy.sh deploy   - Deploy/update application code
#   ./deploy.sh restart  - Restart all services
#   ./deploy.sh status   - Check service status
#   ./deploy.sh logs     - Tail all logs
# ============================================================

APP_DIR="/opt/portfolio"
APP_USER="portfolio"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[+]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# ============================================================
# SETUP - Run once on fresh server
# ============================================================
cmd_setup() {
    [[ $EUID -ne 0 ]] && err "Setup must be run as root"

    log "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq

    log "Installing dependencies..."
    apt-get install -y -qq \
        python3 python3-venv python3-pip \
        nodejs npm sqlite3 gettext \
        debian-keyring debian-archive-keyring apt-transport-https curl

    # Install Caddy
    if ! command -v caddy &> /dev/null; then
        log "Installing Caddy..."
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
        apt-get update -qq
        apt-get install -y -qq caddy
    else
        log "Caddy already installed"
    fi

    # Create app user
    if ! id "$APP_USER" &>/dev/null; then
        log "Creating user '$APP_USER'..."
        useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"
    else
        log "User '$APP_USER' already exists"
    fi

    # Create directory structure
    log "Creating directories..."
    mkdir -p "$APP_DIR"/{backend,frontend,uploads,data}
    mkdir -p /var/log/{portfolio,caddy}

    # Python virtual environment
    log "Setting up Python virtual environment..."
    python3 -m venv "$APP_DIR/venv"
    "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
    "$APP_DIR/venv/bin/pip" install --quiet gunicorn flask

    # Environment file
    if [[ ! -f "$APP_DIR/.env" ]]; then
        log "Creating .env from template..."
        cp "$REPO_DIR/.env.example" "$APP_DIR/.env"
        # Generate a random secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/^SECRET_KEY=changeme$/SECRET_KEY=$SECRET_KEY/" "$APP_DIR/.env"
        warn "Edit $APP_DIR/.env to set DOMAIN, ADMIN_PASSWORD_HASH, etc."
        warn "Generate password hash with: python3 $REPO_DIR/generate_hash.py"
    else
        log ".env already exists, skipping"
    fi

    # Install systemd services
    log "Installing systemd services..."
    cp "$REPO_DIR/portfolio-backend.service" /etc/systemd/system/
    cp "$REPO_DIR/portfolio-frontend.service" /etc/systemd/system/
    systemctl daemon-reload

    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" /var/log/portfolio

    log "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit $APP_DIR/.env (set DOMAIN, ADMIN_PASSWORD_HASH)"
    echo "  2. Run: $0 deploy"
    echo "  3. Run: $0 restart"
}

# ============================================================
# DEPLOY - Deploy/update application code
# ============================================================
cmd_deploy() {
    [[ $EUID -ne 0 ]] && err "Deploy must be run as root"
    [[ ! -f "$APP_DIR/.env" ]] && err ".env not found. Run setup first."

    # Load env for domain
    source "$APP_DIR/.env"

    # Deploy backend
    log "Deploying backend..."
    rsync -a --delete \
        "$REPO_DIR/../backend/" \
        "$APP_DIR/backend/" \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='portfolio.db' \
        --exclude='uploads'

    # Install Python dependencies
    log "Installing Python dependencies..."
    "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/backend/requirements.txt"

    # Deploy frontend
    log "Deploying frontend source..."
    rsync -a --delete \
        "$REPO_DIR/../frontend/" \
        "$APP_DIR/frontend/" \
        --exclude='node_modules' \
        --exclude='build' \
        --exclude='.svelte-kit'

    # Build frontend
    log "Installing npm packages..."
    cd "$APP_DIR/frontend"
    npm ci --silent

    log "Building frontend..."
    npm run build

    # Deploy Caddy config
    log "Deploying Caddy config..."
    # Expand env vars in Caddyfile
    export DOMAIN BACKEND_PORT FRONTEND_PORT
    envsubst '${DOMAIN} ${BACKEND_PORT} ${FRONTEND_PORT}' \
        < "$REPO_DIR/Caddyfile" \
        > /etc/caddy/Caddyfile

    # Fix ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR/backend" "$APP_DIR/frontend"

    # Initialize database if needed
    if [[ ! -f "$APP_DIR/data/portfolio.db" ]]; then
        log "Initializing database..."
        cd "$APP_DIR/backend"
        sudo -u "$APP_USER" \
            DB_PATH="$APP_DIR/data/portfolio.db" \
            "$APP_DIR/venv/bin/python" -c "from database import init_db; init_db()"
        log "Database created at $APP_DIR/data/portfolio.db"
    else
        log "Database already exists, skipping init"
    fi

    log "Deploy complete! Run '$0 restart' to apply changes."
}

# ============================================================
# RESTART - Restart all services
# ============================================================
cmd_restart() {
    [[ $EUID -ne 0 ]] && err "Restart must be run as root"

    log "Restarting services..."
    systemctl restart portfolio-backend
    systemctl restart portfolio-frontend
    systemctl reload caddy

    log "Enabling services on boot..."
    systemctl enable portfolio-backend
    systemctl enable portfolio-frontend
    systemctl enable caddy

    sleep 2
    cmd_status
}

# ============================================================
# STATUS - Check service status
# ============================================================
cmd_status() {
    echo "=== Service Status ==="
    for svc in caddy portfolio-backend portfolio-frontend; do
        status=$(systemctl is-active "$svc" 2>/dev/null || echo "inactive")
        if [[ "$status" == "active" ]]; then
            echo -e "  ${GREEN}●${NC} $svc"
        else
            echo -e "  ${RED}●${NC} $svc ($status)"
        fi
    done
    echo ""

    # Quick health check
    source "$APP_DIR/.env" 2>/dev/null || true
    if curl -sf "http://localhost:${BACKEND_PORT:-8000}/api/health" > /dev/null 2>&1; then
        echo -e "  Backend API: ${GREEN}healthy${NC}"
    else
        echo -e "  Backend API: ${RED}unreachable${NC}"
    fi
}

# ============================================================
# LOGS - Tail logs
# ============================================================
cmd_logs() {
    echo "=== Tailing logs (Ctrl+C to stop) ==="
    journalctl -u portfolio-backend -u portfolio-frontend -u caddy -f --no-hostname
}

# ============================================================
# STOP - Stop all services
# ============================================================
cmd_stop() {
    [[ $EUID -ne 0 ]] && err "Stop must be run as root"
    log "Stopping services..."
    systemctl stop portfolio-backend portfolio-frontend
    log "Services stopped (Caddy still running)"
}

# ============================================================
# Main
# ============================================================
case "${1:-}" in
    setup)   cmd_setup   ;;
    deploy)  cmd_deploy  ;;
    restart) cmd_restart ;;
    status)  cmd_status  ;;
    logs)    cmd_logs    ;;
    stop)    cmd_stop    ;;
    *)
        echo "Usage: $0 {setup|deploy|restart|status|logs|stop}"
        echo ""
        echo "Commands:"
        echo "  setup    - First-time server setup (install deps, create user/dirs)"
        echo "  deploy   - Deploy/update application code and build frontend"
        echo "  restart  - Restart all services"
        echo "  status   - Check service status"
        echo "  logs     - Tail all service logs"
        echo "  stop     - Stop backend and frontend services"
        exit 1
        ;;
esac
