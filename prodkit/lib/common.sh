#!/usr/bin/env bash
# shellcheck shell=bash
# =============================================================================
# ARFA production kit - shared helpers (sourced by every script, never run).
# مكتبة مشتركة لجميع سكربتات النشر - لا تُشغَّل مباشرة.
#
# Isolation contract (zero conflict with other apps on the same VPS):
#   compose project : arfa_prod            containers : arfa_prod-<service>-N
#   network         : arfa_prod_net        volumes    : arfa_prod_db, arfa_prod_odoo
#   database        : arfa_prod (own PostgreSQL container, never published)
#   host ports      : 127.0.0.1:${ARFA_HTTP_PORT}/${ARFA_CHAT_PORT} + public ${ARFA_TRIAL_PORT}
#   nginx           : one file arfa_prod.conf, upstreams/zones/maps prefixed arfa_prod_
#   cron            : /etc/cron.d/arfa_prod_backup        logs: /var/log/arfa_prod_*.log
# =============================================================================
set -euo pipefail

KIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ARFA_ENV_FILE:-$KIT_DIR/.env}"
ENV_EXAMPLE="$KIT_DIR/.env.example"
RUNTIME_DIR="$KIT_DIR/runtime"
STATE_FILE="$RUNTIME_DIR/state"
COMPOSE_FILE="$KIT_DIR/docker-compose.prod.yml"
NGINX_COMPOSE_FILE="$KIT_DIR/docker-compose.nginx.yml"
PROJECT="arfa_prod"
KIT_MARKER="# ARFA-PRODKIT managed file"

# ----------------------------------------------------------------- output ----
if [ -t 1 ]; then
    C_R=$'\e[31m'; C_G=$'\e[32m'; C_Y=$'\e[33m'; C_B=$'\e[36m'; C_0=$'\e[0m'
else
    C_R=""; C_G=""; C_Y=""; C_B=""; C_0=""
fi
# Every message is bilingual:  info "English" "العربية"
info() { printf '%s[i]%s %s\n    %s\n' "$C_B" "$C_0" "$1" "${2:-}"; }
ok()   { printf '%s[OK]%s %s\n    %s\n' "$C_G" "$C_0" "$1" "${2:-}"; }
warn() { printf '%s[!]%s %s\n    %s\n' "$C_Y" "$C_0" "$1" "${2:-}" >&2; }
err()  { printf '%s[X]%s %s\n    %s\n' "$C_R" "$C_0" "$1" "${2:-}" >&2; }
die()  { err "$1" "${2:-}"; exit 1; }
step() { printf '\n%s==> %s | %s%s\n' "$C_B" "$1" "${2:-}" "$C_0"; }

need_root() {
    [ "$(id -u)" -eq 0 ] || die "Run as root (sudo $0 ...)." "شغّل السكربت بصلاحية root (استخدم sudo)."
}
have() { command -v "$1" >/dev/null 2>&1; }
ts_now() { date +%Y%m%d_%H%M%S; }

confirm() { # confirm "question EN" "سؤال" -> returns 0 when the user types yes
    local a
    [ "${ARFA_ASSUME_YES:-0}" = "1" ] && return 0
    printf '%s?%s %s\n    %s\n    [type yes / اكتب yes]: ' "$C_Y" "$C_0" "$1" "${2:-}"
    read -r a || return 1
    [ "$a" = "yes" ] || [ "$a" = "YES" ] || [ "$a" = "y" ]
}

# ------------------------------------------------------------------- env ----
set_defaults() {
    : "${ARFA_HOME:=/opt/arfa}"
    : "${ARFA_ADDONS_DIR:=$ARFA_HOME/custom_addons}"
    : "${ARFA_BACKUP_DIR:=$ARFA_HOME/backups}"
    : "${ARFA_DB_NAME:=arfa_prod}"
    : "${ARFA_DB_USER:=odoo}"
    : "${ARFA_DB_PASSWORD:=}"
    : "${ARFA_ADMIN_PASSWD:=}"
    : "${ARFA_ODOO_IMAGE:=odoo:19.0}"
    : "${ARFA_PG_IMAGE:=postgres:16}"
    : "${ARFA_NGINX_IMAGE:=nginx:1.27-alpine}"
    : "${ARFA_HTTP_PORT:=18069}"
    : "${ARFA_CHAT_PORT:=18072}"
    : "${ARFA_TRIAL_PORT:=8090}"
    : "${ARFA_PUBLIC_IP:=}"
    : "${ARFA_TRIAL_AUTH:=1}"
    : "${ARFA_TRIAL_AUTH_USER:=arfa}"
    : "${ARFA_TRIAL_AUTH_PASSWORD:=}"
    : "${ARFA_NGINX_MODE:=auto}"
    : "${ARFA_NGINX_LISTEN_IP:=}"
    : "${ARFA_IPV6:=auto}"
    : "${ARFA_HTTP2:=auto}"
    : "${ARFA_DOMAIN:=arfa-sa.com}"
    : "${ARFA_CANONICAL:=apex}"
    : "${ARFA_LE_EMAIL:=}"
    : "${ARFA_HSTS:=0}"
    : "${ARFA_KEEP_TRIAL_AFTER_DOMAIN:=0}"
    : "${ARFA_ACME_WEBROOT:=/var/www/arfa_prod_acme}"
    : "${ARFA_WORKERS:=auto}"
    : "${ARFA_WORKERS_CAP:=4}"
    : "${ARFA_ODOO_MEM:=4g}"
    : "${ARFA_DB_MEM:=1g}"
    : "${ARFA_NGINX_MEM:=256m}"
    : "${ARFA_PG_SHARED_BUFFERS:=256MB}"
    : "${ARFA_PG_MAX_CONNECTIONS:=200}"
    : "${ARFA_BACKUP_KEEP_DAYS:=14}"
    : "${ARFA_NOINDEX_PARAM:=wasm_website.hide_from_search_engines}"
    : "${ARFA_UPDATE_MODULES:=wasm_website,wasm_debrand}"
    export ARFA_HOME ARFA_ADDONS_DIR ARFA_BACKUP_DIR ARFA_DB_NAME ARFA_DB_USER ARFA_ODOO_IMAGE \
        ARFA_PG_IMAGE ARFA_NGINX_IMAGE ARFA_HTTP_PORT ARFA_CHAT_PORT ARFA_TRIAL_PORT ARFA_ODOO_MEM \
        ARFA_DB_MEM ARFA_NGINX_MEM ARFA_PG_SHARED_BUFFERS ARFA_PG_MAX_CONNECTIONS ARFA_ACME_WEBROOT
}

load_env() {
    if [ -f "$ENV_FILE" ]; then
        set -a; # shellcheck disable=SC1090
        . "$ENV_FILE"; set +a
    fi
    set_defaults
    case "$ARFA_DB_NAME" in
        *[!a-z0-9_]*|"") die "ARFA_DB_NAME must be lowercase letters/digits/_ only." "اسم قاعدة البيانات يجب أن يكون حروفاً صغيرة وأرقاماً و _ فقط.";;
    esac
}

# set_env KEY VALUE : create or replace one line in .env (idempotent)
set_env() {
    local key="$1" val="$2" tmp
    [ -f "$ENV_FILE" ] || die ".env missing: $ENV_FILE" "ملف .env غير موجود"
    tmp="$(mktemp "$ENV_FILE.XXXX")"
    grep -v -E "^${key}=" "$ENV_FILE" > "$tmp" || true
    printf '%s=%s\n' "$key" "$val" >> "$tmp"
    chmod 600 "$tmp"; mv "$tmp" "$ENV_FILE"
    printf -v "$key" '%s' "$val"; export "${key?}"
}

state_get() { [ -f "$STATE_FILE" ] && grep -E "^$1=" "$STATE_FILE" | tail -1 | cut -d= -f2- || true; }
state_set() {
    mkdir -p "$RUNTIME_DIR"; touch "$STATE_FILE"
    local tmp; tmp="$(mktemp "$STATE_FILE.XXXX")"
    grep -v -E "^$1=" "$STATE_FILE" > "$tmp" || true
    printf '%s=%s\n' "$1" "$2" >> "$tmp"; mv "$tmp" "$STATE_FILE"
}

gen_secret() { openssl rand -hex "${1:-24}"; }
gen_readable() { openssl rand -base64 32 | tr -dc 'A-HJ-NP-Za-km-z2-9' | head -c "${1:-14}"; }

detect_public_ip() {
    local ip=""
    if have curl; then
        ip="$(curl -4 -fsS --max-time 5 https://api.ipify.org 2>/dev/null || true)"
        [ -n "$ip" ] || ip="$(curl -4 -fsS --max-time 5 https://ifconfig.me 2>/dev/null || true)"
    fi
    if ! grep -Eq '^[0-9]+(\.[0-9]+){3}$' <<< "$ip"; then
        ip="$(ip -4 route get 1.1.1.1 2>/dev/null | sed -n 's/.* src \([0-9.]*\).*/\1/p' | head -1)"
    fi
    printf '%s' "$ip"
}

compute_workers() {
    local cpus w
    if [ "$ARFA_WORKERS" != "auto" ]; then printf '%s' "$ARFA_WORKERS"; return; fi
    cpus="$(nproc 2>/dev/null || echo 1)"
    w=$(( 2 * cpus + 1 ))
    [ "$w" -gt "$ARFA_WORKERS_CAP" ] && w="$ARFA_WORKERS_CAP"
    [ "$w" -lt 2 ] && w=3
    printf '%s' "$w"
}

# --------------------------------------------------------------- docker ----
nginx_mode() { # effective nginx mode: host | container
    local m; m="$(state_get nginx_mode)"
    [ -n "$m" ] && { printf '%s' "$m"; return; }
    if [ "$ARFA_NGINX_MODE" != "auto" ]; then printf '%s' "$ARFA_NGINX_MODE"; return; fi
    if host_nginx_present; then printf 'host'; else printf 'container'; fi
}

host_nginx_present() {
    have nginx && [ -f /etc/nginx/nginx.conf ] || return 1
    if have systemctl && systemctl is-active --quiet nginx 2>/dev/null; then return 0; fi
    # not managed by systemd: accept if an nginx master runs and no container runs an nginx image
    pgrep -f 'nginx: master process' >/dev/null 2>&1 || return 1
    local imgs; imgs="$(docker ps --format '{{.Image}}' 2>/dev/null || true)"
    [[ "${imgs,,}" != *nginx* ]]
}

# dc ... : docker compose bound to this project only
dc() {
    local files=(-f "$COMPOSE_FILE") prof=""
    if [ "$(state_get nginx_mode)" = "container" ]; then
        files+=(-f "$NGINX_COMPOSE_FILE")
        prof="$(state_get mode)"
        case "$prof" in trial|domain) ;; *) prof="";; esac
    fi
    COMPOSE_PROFILES="$prof" docker compose -p "$PROJECT" --env-file "$ENV_FILE" "${files[@]}" "$@"
}

require_docker() {
    have docker || die "Docker is not installed." "Docker غير مثبت. ثبّته أولاً (https://docs.docker.com/engine/install/)."
    docker info >/dev/null 2>&1 || die "Docker daemon not reachable." "لا يمكن الاتصال بخدمة Docker (هل هي تعمل؟ هل أنت root؟)."
    docker compose version >/dev/null 2>&1 || die "Docker Compose v2 plugin missing (docker compose)." "إضافة Docker Compose v2 غير مثبتة."
}

require_env_file() {
    [ -f "$ENV_FILE" ] || die "No .env found - run install.sh first." "لا يوجد ملف .env - شغّل install.sh أولاً."
}

wait_healthy() { # wait_healthy <service> <timeout-seconds>
    local svc="$1" t="${2:-180}" cid st i=0
    while [ "$i" -lt "$t" ]; do
        cid="$(dc ps -q "$svc" 2>/dev/null | head -1)"
        if [ -n "$cid" ]; then
            st="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" 2>/dev/null || true)"
            [ "$st" = "healthy" ] && return 0
        fi
        sleep 3; i=$((i + 3))
    done
    return 1
}

psql_db() { # psql_db <dbname> [psql args...]   (stdin passes through)
    local db="$1"; shift
    dc exec -T db psql -X -q -v ON_ERROR_STOP=1 -U "$ARFA_DB_USER" -d "$db" "$@"
}

db_exists() {
    [ "$(psql_db postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${ARFA_DB_NAME}'" 2>/dev/null | tr -d '[:space:]')" = "1" ]
}

# set_param KEY VALUE  - upsert ir.config_parameter (Odoo must be restarted to drop caches)
set_param() {
    psql_db "$ARFA_DB_NAME" -v k="$1" -v v="$2" <<'SQL'
UPDATE ir_config_parameter SET value = :'v', write_date = (now() at time zone 'UTC') WHERE key = :'k';
INSERT INTO ir_config_parameter (key, value, create_uid, write_uid, create_date, write_date)
SELECT :'k', :'v', 1, 1, (now() at time zone 'UTC'), (now() at time zone 'UTC')
WHERE NOT EXISTS (SELECT 1 FROM ir_config_parameter WHERE key = :'k');
SQL
}

# set_website_domain URL|''  - Website > Settings > Domain (single-website installs only)
set_website_domain() {
    psql_db "$ARFA_DB_NAME" -v d="$1" <<'SQL'
UPDATE website SET domain = NULLIF(:'d', '') WHERE (SELECT count(*) FROM website) = 1;
SQL
}

# apply_mode_params trial|domain  - base URL, freeze, noindex switch, website domain
apply_mode_params() {
    local mode="$1" url
    if [ "$mode" = "domain" ]; then
        url="https://$(canonical_host)"
        set_param web.base.url "$url"
        set_param "$ARFA_NOINDEX_PARAM" "False"
        set_website_domain "$url"
    else
        url="$(trial_url)"
        set_param web.base.url "$url"
        set_param "$ARFA_NOINDEX_PARAM" "True"
        set_website_domain ""
    fi
    set_param web.base.url.freeze "True"
    info "web.base.url = $url (frozen)" "تم ضبط رابط الموقع الأساسي وتثبيته: $url"
}

trial_url() { printf 'http://%s:%s' "${ARFA_PUBLIC_IP:-SERVER_IP}" "$ARFA_TRIAL_PORT"; }
canonical_host() { if [ "$ARFA_CANONICAL" = "www" ]; then printf 'www.%s' "$ARFA_DOMAIN"; else printf '%s' "$ARFA_DOMAIN"; fi; }

render_odoo_conf() {
    local workers tpl="$KIT_DIR/config/odoo.conf.template" out="$RUNTIME_DIR/odoo.conf"
    [ -n "$ARFA_DB_PASSWORD" ] && [ -n "$ARFA_ADMIN_PASSWD" ] || die "Passwords missing in .env" "كلمات المرور غير موجودة في .env"
    workers="$(compute_workers)"
    mkdir -p "$RUNTIME_DIR"; chmod 700 "$RUNTIME_DIR"
    sed -e "s|@ARFA_DB_NAME@|$ARFA_DB_NAME|g" \
        -e "s|@ARFA_DB_USER@|$ARFA_DB_USER|g" \
        -e "s|@ARFA_DB_PASSWORD@|$ARFA_DB_PASSWORD|g" \
        -e "s|@ARFA_ADMIN_PASSWD@|$ARFA_ADMIN_PASSWD|g" \
        -e "s|@ARFA_WORKERS@|$workers|g" "$tpl" > "$out.tmp"
    if grep -q '@ARFA_' "$out.tmp"; then rm -f "$out.tmp"; die "Unrendered placeholder in odoo.conf" "قالب odoo.conf يحتوي متغيرات غير معبأة"; fi
    # write in place (not mv): single-file bind mounts keep pointing at the original inode
    cat "$out.tmp" > "$out"; rm -f "$out.tmp"
    printf '%s' "$ARFA_DB_PASSWORD" > "$RUNTIME_DIR/db_password"
    # runtime/ is 0700 root: host users cannot reach these files; 0644 lets the
    # container users (odoo uid 101 / postgres uid 999) read their bind mounts.
    chmod 644 "$out" "$RUNTIME_DIR/db_password"
    info "odoo.conf rendered (workers=$workers)" "تم إنشاء ملف إعدادات أودو (عدد العمال=$workers)"
}

# --------------------------------------------------- backup/restore core ----
# restore_db <dump-file>  : DB must NOT exist (caller drops it); db service up
restore_db() {
    local dump="$1" log="$RUNTIME_DIR/logs/restore_db_$(ts_now).log" rc=0 head n
    [ -f "$dump" ] || die "Dump not found: $dump" "ملف النسخة غير موجود: $dump"
    head="$(head -c 5 "$dump" | tr -d '\0')"
    [ "$head" = "PGDMP" ] || die "Not a pg_dump custom-format file (-Fc): $dump" "الملف ليس نسخة pg_dump بصيغة custom (-Fc)."
    mkdir -p "$RUNTIME_DIR/logs"
    local ver
    ver="$(dc exec -T db pg_restore -l < "$dump" 2>/dev/null | sed -n 's/.*Dumped from database version: \([0-9]*\).*/\1/p' | head -1 || true)"
    info "Dump made by PostgreSQL ${ver:-?} (target: 16)" "النسخة مأخوذة من PostgreSQL ${ver:-?}"
    if [ -n "$ver" ] && [ "$ver" -gt 16 ]; then die "Dump is from PostgreSQL $ver > 16" "النسخة من إصدار أحدث من 16 ولا يمكن استعادتها"; fi
    psql_db postgres -c "CREATE DATABASE \"$ARFA_DB_NAME\" OWNER \"$ARFA_DB_USER\" ENCODING 'UTF8' TEMPLATE template0"
    info "Restoring database (may take minutes)..." "جاري استعادة قاعدة البيانات (قد يستغرق دقائق)..."
    dc exec -T db pg_restore -U "$ARFA_DB_USER" -d "$ARFA_DB_NAME" --no-owner --no-privileges < "$dump" > "$log" 2>&1 || rc=$?
    n="$(psql_db "$ARFA_DB_NAME" -tAc "SELECT count(*) FROM ir_module_module WHERE state='installed'" 2>/dev/null | tr -d '[:space:]' || true)"
    if ! [ "${n:-0}" -gt 0 ] 2>/dev/null; then
        tail -20 "$log" >&2
        die "Restore failed (no installed modules found). Log: $log" "فشلت الاستعادة. راجع السجل: $log"
    fi
    [ "$rc" -ne 0 ] && warn "pg_restore reported warnings (rc=$rc) - DB looks valid. Log: $log" "ظهرت تحذيرات أثناء الاستعادة لكن القاعدة سليمة. السجل: $log"
    ok "Database $ARFA_DB_NAME restored ($n modules installed)" "تمت استعادة قاعدة البيانات ($n موديول مثبت)"
}

# restore_filestore <dir|tar.gz>  : replaces filestore/<db> inside volume arfa_prod_odoo
restore_filestore() {
    local src="$1" abs
    [ -e "$src" ] || die "Filestore not found: $src" "مجلد/أرشيف الملفات غير موجود: $src"
    abs="$(cd "$(dirname "$src")" && pwd)/$(basename "$src")"
    info "Restoring filestore from $abs ..." "جاري استعادة ملفات الموقع (الصور والفيديو)..."
    # shellcheck disable=SC2016
    dc run --rm -T --no-deps --user 0 -v "$abs:/restore_src:ro" --entrypoint bash odoo -c '
set -euo pipefail
DB="$1"; SRC=/restore_src; BASE=/var/lib/odoo/filestore; STAGE=/var/lib/odoo/.arfa_restore_tmp
rm -rf "$STAGE" "$BASE/$DB.new"; mkdir -p "$STAGE" "$BASE"
if [ -f "$SRC" ]; then tar -xzf "$SRC" -C "$STAGE"; ROOT="$STAGE"; else ROOT="$SRC"; fi
hashdir() { find "$1" -mindepth 1 -maxdepth 1 -type d -regextype posix-egrep -regex ".*/[0-9a-f]{2}" -print -quit; }
for _ in 1 2 3 4 5; do
  if [ -n "$(hashdir "$ROOT")" ]; then break; fi
  mapfile -t SUB < <(find "$ROOT" -mindepth 1 -maxdepth 1 -type d)
  if [ "${#SUB[@]}" -eq 1 ]; then ROOT="${SUB[0]}"; else echo "Cannot find filestore root (folders 00..ff) in source" >&2; exit 3; fi
done
[ -n "$(hashdir "$ROOT")" ] || { echo "No filestore hash folders found" >&2; exit 3; }
mkdir -p "$BASE/$DB.new"; cp -a "$ROOT/." "$BASE/$DB.new/"
rm -rf "$BASE/$DB"; mv "$BASE/$DB.new" "$BASE/$DB"; rm -rf "$STAGE"
chown -R odoo:odoo /var/lib/odoo
echo "files=$(find "$BASE/$DB" -type f | wc -l) owner=$(id -u odoo):$(id -g odoo) source_root=${ROOT#/restore_src}"
' _ "$ARFA_DB_NAME" || die "Filestore restore failed" "فشلت استعادة الملفات"
    ok "Filestore restored into volume arfa_prod_odoo:/var/lib/odoo/filestore/$ARFA_DB_NAME" "تمت استعادة الملفات"
}

drop_db() {
    psql_db postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${ARFA_DB_NAME}' AND pid <> pg_backend_pid()" >/dev/null
    psql_db postgres -c "DROP DATABASE IF EXISTS \"$ARFA_DB_NAME\""
}

# odoo_update <modules> : stop odoo, run -u, return rc (log in runtime/logs)
odoo_update() {
    local mods="$1" log="$RUNTIME_DIR/logs/update_$(ts_now).log" rc=0
    mkdir -p "$RUNTIME_DIR/logs"
    info "Updating modules: $mods" "تحديث الموديولات: $mods"
    dc stop odoo >/dev/null 2>&1 || true
    dc run --rm -T --no-deps odoo odoo -d "$ARFA_DB_NAME" -u "$mods" --stop-after-init \
        --no-http --max-cron-threads=0 --workers=0 > "$log" 2>&1 || rc=$?
    if [ "$rc" -eq 0 ] && grep -Eq ' (CRITICAL|ERROR) .*odoo\.(modules|addons|registry)' "$log"; then rc=9; fi
    if [ "$rc" -ne 0 ]; then
        grep -E ' (CRITICAL|ERROR) ' "$log" | tail -15 >&2 || tail -20 "$log" >&2
        err "Module update failed (rc=$rc). Log: $log" "فشل تحديث الموديولات. السجل: $log"
        return "$rc"
    fi
    ok "Modules updated. Log: $log" "تم تحديث الموديولات بنجاح"
}

find_filestore_in() { # find_filestore_in DIR -> prints best filestore candidate (dir or tar.gz)
    local d="$1" c
    c="$(find "$d" -maxdepth 1 \( -iname '*filestore*.tar.gz' -o -iname '*filestore*.tgz' \) -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
    [ -z "$c" ] && c="$(find "$d" -maxdepth 1 -iname '*filestore*' -type d -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
    if [ -z "$c" ]; then   # e.g. C:\arfa\backups\arfa2026\ (folder named after the DB): accept a single sub-folder
        local subs; subs="$(find "$d" -mindepth 1 -maxdepth 1 -type d ! -name '.*' 2>/dev/null)"
        [ -n "$subs" ] && [ "$(wc -l <<< "$subs")" -eq 1 ] && c="$subs"
    fi
    printf '%s' "$c"
}
find_dump_in() {
    find "$1" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-
}
find_filestore_for() { # find_filestore_for DUMP -> sibling "<name>_filestore.tar.gz" or best candidate in its folder
    local b="${1%.dump}"
    if [ -f "${b}_filestore.tar.gz" ]; then printf '%s' "${b}_filestore.tar.gz"; return; fi
    find_filestore_in "$(dirname "$1")"
}
