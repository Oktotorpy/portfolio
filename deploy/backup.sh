#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Portfolio CMS - Backup Script
# Backs up SQLite database and uploaded files
# Usage: ./backup.sh [backup_dir]
# Suggested cron: 0 3 * * * /opt/portfolio/deploy/backup.sh
# ============================================================

APP_DIR="/opt/portfolio"
BACKUP_DIR="${1:-$APP_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
KEEP_DAYS=30

mkdir -p "$BACKUP_DIR"

# Backup SQLite using .backup command (safe, handles WAL)
echo "[+] Backing up database..."
if [[ -f "$APP_DIR/data/portfolio.db" ]]; then
    sqlite3 "$APP_DIR/data/portfolio.db" ".backup '$BACKUP_DIR/portfolio_${TIMESTAMP}.db'"
    echo "    → $BACKUP_DIR/portfolio_${TIMESTAMP}.db"
else
    echo "    No database found, skipping"
fi

# Backup uploads
echo "[+] Backing up uploads..."
if [[ -d "$APP_DIR/uploads" ]] && [[ -n "$(ls -A "$APP_DIR/uploads" 2>/dev/null)" ]]; then
    tar -czf "$BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz" -C "$APP_DIR" uploads/
    echo "    → $BACKUP_DIR/uploads_${TIMESTAMP}.tar.gz"
else
    echo "    No uploads found, skipping"
fi

# Clean old backups
echo "[+] Cleaning backups older than ${KEEP_DAYS} days..."
find "$BACKUP_DIR" -type f -mtime +${KEEP_DAYS} -delete 2>/dev/null || true

echo "[+] Backup complete"
ls -lh "$BACKUP_DIR"/*_${TIMESTAMP}* 2>/dev/null || true
