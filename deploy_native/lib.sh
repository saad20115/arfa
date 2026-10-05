#!/usr/bin/env bash
# shared helpers for the ARFA native deployment scripts
set -euo pipefail
KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=config.env
. "$KIT_DIR/config.env"
[ -f "$KIT_DIR/config.local.env" ] && . "$KIT_DIR/config.local.env"
SECRETS="$CONF_DIR/secrets.env"
ODOO_CONF="$CONF_DIR/arfa.conf"
NGINX_SITE=/etc/nginx/sites-available/arfa_new.conf
NGINX_LINK=/etc/nginx/sites-enabled/arfa_new.conf
HTPASSWD=/etc/nginx/arfa_new.htpasswd
UNIT=/etc/systemd/system/$SERVICE.service
PYTHON="$ARFA_RUNTIME/venv/bin/python3"
ODOO_BIN="$ARFA_RUNTIME/odoo/odoo-bin"
[ -n "${PGHOST_OVERRIDE:-}" ] && export PGHOST="$PGHOST_OVERRIDE"
[ -n "${PGPORT_OVERRIDE:-}" ] && export PGPORT="$PGPORT_OVERRIDE"

c_ok=$'\e[32m'; c_err=$'\e[31m'; c_warn=$'\e[33m'; c_inf=$'\e[36m'; c_off=$'\e[0m'
step() { printf '\n%s==== %s | %s ====%s\n' "$c_inf" "$1" "$2" "$c_off"; }
ok()   { printf '%s[OK]%s %s | %s\n' "$c_ok" "$c_off" "$1" "${2:-}"; }
warn() { printf '%s[!]%s %s | %s\n' "$c_warn" "$c_off" "$1" "${2:-}"; }
die()  { printf '%s[FAIL]%s %s | %s\n' "$c_err" "$c_off" "$1" "${2:-}" >&2; exit 1; }
need_root() { [ "$(id -u)" = 0 ] || die "Run as root (sudo)" "شغّل الأمر كـ root"; }
as_pg() { sudo -u postgres env ${PGHOST:+PGHOST=$PGHOST} ${PGPORT:+PGPORT=$PGPORT} "$@"; }
psql_su() { as_pg psql -v ON_ERROR_STOP=1 -X "$@"; }
psql_db() { as_pg psql -v ON_ERROR_STOP=1 -X -d "$DB_NAME" "$@"; }
port_busy() { ss -ltnH "( sport = :$1 )" 2>/dev/null | grep -q .; }
db_exists() { [ "$(psql_su -Atc "select 1 from pg_database where datname='$DB_NAME'")" = 1 ]; }
role_exists() { [ "$(psql_su -Atc "select 1 from pg_roles where rolname='$ARFA_USER'")" = 1 ]; }
server_ip() { hostname -I 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+\.' | grep -vE '^(10|127|172\.(1[6-9]|2[0-9]|3[01])|192\.168)\.' | head -1; }
odoo_run() { sudo -u "$ARFA_USER" "$PYTHON" "$ODOO_BIN" -c "$ODOO_CONF" "$@"; }
odoo_shell() { sudo -u "$ARFA_USER" "$PYTHON" "$ODOO_BIN" shell -c "$ODOO_CONF" "$@"; }
confirm() { [ "${ASSUME_YES:-0}" = 1 ] && return 0; read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy] ]]; }
