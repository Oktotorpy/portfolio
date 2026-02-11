#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Portfolio CMS - Server Setup & Deployment Script
# Run as root on Ubuntu 24.04 VPS
#
# Usage:
#   ./deploy.sh setup              - First-time server setup
#   ./deploy.sh git-init <REPO>    - Connect server to GitHub repo
#   ./deploy.sh pull               - Pull latest code & rebuild
#   ./deploy.sh restart            - Restart all services
#   ./deploy.sh status             - Check service status
#   ./deploy.sh logs               - Tail all logs
#   ./deploy.sh stop               - Stop services
# ============================================================

APP_DIR="/opt/portfolio"
APP_USER="portfolio"
REPO_DIR="$APP_DIR/repo"

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
        nodejs npm sqlite3 gettext git \
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
    mkdir -p "$APP_DIR"/{uploads,data}
    mkdir -p /var/log/{portfolio,caddy}

    # Python virtual environment
    log "Setting up Python virtual environment..."
    python3 -m venv "$APP_DIR/venv"
    "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip
    "$APP_DIR/venv/bin/pip" install --quiet gunicorn flask

    # Environment file
    if [[ ! -f "$APP_DIR/.env" ]]; then
        if [[ -f "$REPO_DIR/deploy/.env.example" ]]; then
            cp "$REPO_DIR/deploy/.env.example" "$APP_DIR/.env"
        else
            cat > "$APP_DIR/.env" <<'ENVEOF'
DOMAIN=your-domain.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=changeme
SECRET_KEY=changeme
DB_PATH=/opt/portfolio/data/portfolio.db
UPLOAD_DIR=/opt/portfolio/uploads
CORS_ORIGIN=https://your-domain.com
BACKEND_PORT=8000
FRONTEND_PORT=3000
INTERNAL_API_URL=http://localhost:8000
ENVEOF
        fi
        # Generate a random secret key
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/^SECRET_KEY=changeme$/SECRET_KEY=$SECRET_KEY/" "$APP_DIR/.env"
        warn "Edit $APP_DIR/.env to set DOMAIN, ADMIN_PASSWORD_HASH, etc."
    else
        log ".env already exists, skipping"
    fi

    # Set ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" /var/log/portfolio

    log "Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. $0 git-init git@github.com:YOUR_USER/YOUR_REPO.git"
    echo "  2. Edit $APP_DIR/.env"
    echo "  3. $0 pull"
}

# ============================================================
# GIT-INIT - Clone repo to server
# ============================================================
cmd_git_init() {
    [[ $EUID -ne 0 ]] && err "Must be run as root"
    local repo_url="${1:-}"
    [[ -z "$repo_url" ]] && err "Usage: $0 git-init <GITHUB_REPO_URL>"

    # Generate deploy key if none exists
    local key_file="/root/.ssh/deploy_key"
    if [[ ! -f "$key_file" ]]; then
        log "Generating SSH deploy key..."
        mkdir -p /root/.ssh
        ssh-keygen -t ed25519 -f "$key_file" -N "" -C "portfolio-deploy"
        chmod 600 "$key_file"

        # Configure SSH to use this key for github.com
        if ! grep -q "deploy_key" /root/.ssh/config 2>/dev/null; then
            cat >> /root/.ssh/config <<EOF
Host github.com
    HostName github.com
    User git
    IdentityFile $key_file
    StrictHostKeyChecking accept-new
EOF
            chmod 600 /root/.ssh/config
        fi

        echo ""
        log "Deploy key generated. Add this as a Deploy Key in your GitHub repo:"
        echo "  Settings → Deploy keys → Add deploy key"
        echo ""
        cat "${key_file}.pub"
        echo ""
        warn "After adding the key to GitHub, run this command again."
        exit 0
    fi

    # Clone or update
    if [[ -d "$REPO_DIR/.git" ]]; then
        log "Repo already cloned. Pulling latest..."
        cd "$REPO_DIR"
        git pull origin main
    else
        log "Cloning repository..."
        rm -rf "$REPO_DIR"
        git clone "$repo_url" "$REPO_DIR"
    fi

    chown -R "$APP_USER:$APP_USER" "$REPO_DIR"
    log "Repository ready at $REPO_DIR"
    echo ""
    echo "Next: $0 pull"
}

# ============================================================
# PULL - Pull latest code from GitHub & rebuild
# ============================================================
cmd_pull() {
    [[ $EUID -ne 0 ]] && err "Must be run as root"
    [[ ! -d "$REPO_DIR/.git" ]] && err "No git repo found. Run: $0 git-init <REPO_URL>"
    [[ ! -f "$APP_DIR/.env" ]] && err ".env not found. Run setup first."

    source "$APP_DIR/.env"

    # Pull latest
    log "Pulling latest from GitHub..."
    cd "$REPO_DIR"
    git fetch origin
    git reset --hard origin/main

    # Deploy backend
    log "Deploying backend..."
    rsync -a --delete \
        "$REPO_DIR/backend/" \
        "$APP_DIR/backend/" \
        --exclude='__pycache__' \
        --exclude='*.pyc'

    log "Installing Python dependencies..."
    "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/backend/requirements.txt"

    # Deploy frontend
    log "Deploying frontend..."
    rsync -a --delete \
        "$REPO_DIR/frontend/" \
        "$APP_DIR/frontend/" \
        --exclude='node_modules' \
        --exclude='build' \
        --exclude='.svelte-kit'

    log "Installing npm packages..."
    cd "$APP_DIR/frontend"
    npm ci --silent 2>/dev/null || npm install --silent

    log "Building frontend..."
    npm run build

    # Deploy Caddy config
    log "Deploying Caddy config..."
    export DOMAIN BACKEND_PORT FRONTEND_PORT
    envsubst '${DOMAIN} ${BACKEND_PORT} ${FRONTEND_PORT}' \
        < "$REPO_DIR/deploy/Caddyfile" \
        > /etc/caddy/Caddyfile

    # Install/update systemd services
    cp "$REPO_DIR/deploy/portfolio-backend.service" /etc/systemd/system/
    cp "$REPO_DIR/deploy/portfolio-frontend.service" /etc/systemd/system/
    systemctl daemon-reload

    # Fix ownership
    chown -R "$APP_USER:$APP_USER" "$APP_DIR/backend" "$APP_DIR/frontend" "$REPO_DIR"

    # Initialize database if needed
    if [[ ! -f "$APP_DIR/data/portfolio.db" ]]; then
        log "Initializing database..."
        cd "$APP_DIR/backend"
        sudo -u "$APP_USER" \
            DB_PATH="$APP_DIR/data/portfolio.db" \
            "$APP_DIR/venv/bin/python" -c "from database import init_db; init_db()"
        log "Database created"
    fi

    # Restart services
    log "Restarting services..."
    systemctl restart portfolio-backend
    systemctl restart portfolio-frontend
    systemctl reload caddy

    systemctl enable portfolio-backend portfolio-frontend caddy 2>/dev/null

    sleep 2
    cmd_status
    log "Deployment complete!"
}

# ============================================================
# RESTART
# ============================================================
cmd_restart() {
    [[ $EUID -ne 0 ]] && err "Must be run as root"
    log "Restarting services..."
    systemctl restart portfolio-backend
    systemctl restart portfolio-frontend
    systemctl reload caddy
    systemctl enable portfolio-backend portfolio-frontend caddy 2>/dev/null
    sleep 2
    cmd_status
}

# ============================================================
# STATUS
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
    source "$APP_DIR/.env" 2>/dev/null || true
    if curl -sf "http://localhost:${BACKEND_PORT:-8000}/api/health" > /dev/null 2>&1; then
        echo -e "  Backend API: ${GREEN}healthy${NC}"
    else
        echo -e "  Backend API: ${RED}unreachable${NC}"
    fi
}

# ============================================================
# LOGS
# ============================================================
cmd_logs() {
    journalctl -u portfolio-backend -u portfolio-frontend -u caddy -f --no-hostname
}

# ============================================================
# STOP
# ============================================================
cmd_stop() {
    [[ $EUID -ne 0 ]] && err "Must be run as root"
    log "Stopping services..."
    systemctl stop portfolio-backend portfolio-frontend
    log "Services stopped (Caddy still running)"
}

# ============================================================
# Main
# ============================================================
case "${1:-}" in
    setup)      cmd_setup ;;
    git-init)   cmd_git_init "${2:-}" ;;
    pull)       cmd_pull ;;
    restart)    cmd_restart ;;
    status)     cmd_status ;;
    logs)       cmd_logs ;;
    stop)       cmd_stop ;;
    *)
        echo "Usage: $0 {setup|git-init|pull|restart|status|logs|stop}"
        echo ""
        echo "Commands:"
        echo "  setup              - First-time server setup"
        echo "  git-init <REPO>    - Connect server to a GitHub repo (SSH)"
        echo "  pull               - Pull latest code, rebuild, restart"
        echo "  restart            - Restart all services"
        echo "  status             - Check service status"
        echo "  logs               - Tail all service logs"
        echo "  stop               - Stop backend and frontend services"
        exit 1
        ;;
esac
