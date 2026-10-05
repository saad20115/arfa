#!/usr/bin/env bash
# =============================================================================
# status.sh - health report of ARFA (containers, Odoo, nginx, cert, backups, isolation).
# تقرير حالة الموقع. لا يغيّر أي شيء.
# Usage: sudo ./status.sh [--logs]      exit code 1 if something critical is down.
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"
. "$(dirname "$0")/lib/nginx.sh"

LOGS=0; [ "${1:-}" = "--logs" ] && LOGS=1
require_docker; require_env_file; load_env
BAD=0
good() { printf '%s[OK]%s   %s\n' "$C_G" "$C_0" "$1"; }
bad()  { printf '%s[DOWN]%s %s\n' "$C_R" "$C_0" "$1"; BAD=$((BAD+1)); }
note() { printf '[--]   %s\n' "$1"; }

MODE="$(state_get mode)"; NM="$(state_get nginx_mode)"
step "ARFA status - phase: ${MODE:-not installed}, nginx: ${NM:-?}" "حالة موقع عرفة"
dc ps --format 'table {{.Name}}\t{{.Status}}\t{{.Ports}}' || true

for s in db odoo; do
    cid="$(dc ps -q "$s" 2>/dev/null | head -1)"
    st="$( [ -n "$cid" ] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$cid" || echo missing)"
    [ "$st" = "healthy" ] && good "$s: $st" || bad "$s: $st"
done
cid="$(dc ps -q odoo 2>/dev/null | head -1)"
[ -n "$cid" ] && note "odoo image: $(docker inspect -f '{{.Config.Image}}' "$cid") digest $(docker image inspect -f '{{index .RepoDigests 0}}' "$(docker inspect -f '{{.Image}}' "$cid")" 2>/dev/null | sed 's/.*@//' | cut -c1-19)"

# isolation checks
pub="$(docker port "$(dc ps -q db 2>/dev/null | head -1)" 2>/dev/null || true)"
[ -z "$pub" ] && good "PostgreSQL not published on the host" || bad "PostgreSQL is published: $pub"
op="$( [ -n "$cid" ] && docker port "$cid" || true)"
if [ -n "$op" ] && ! grep -qv '^[0-9/a-z]* -> 127\.0\.0\.1:' <<< "$op"; then good "Odoo bound to 127.0.0.1 only ($(tr '\n' ' ' <<< "$op"))"; else bad "Odoo ports: ${op:-none}"; fi

code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:$ARFA_HTTP_PORT/web/health" || true)"
[ "$code" = "200" ] && good "Odoo /web/health on 127.0.0.1:$ARFA_HTTP_PORT" || bad "Odoo /web/health -> $code"
if [ -n "$cid" ] && db_exists 2>/dev/null; then
    burl="$(psql_db "$ARFA_DB_NAME" -tAc "SELECT value FROM ir_config_parameter WHERE key='web.base.url'" | tr -d '[:space:]')"
    noidx="$(psql_db "$ARFA_DB_NAME" -tAc "SELECT value FROM ir_config_parameter WHERE key='$ARFA_NOINDEX_PARAM'" | tr -d '[:space:]')"
    wdom="$(psql_db "$ARFA_DB_NAME" -tAc "SELECT string_agg(coalesce(domain,'(empty)'), ', ') FROM website" | tr -d '[:space:]')"
    note "web.base.url=$burl | $ARFA_NOINDEX_PARAM=${noidx:-unset} | website.domain=$wdom"
    note "DB size: $(psql_db "$ARFA_DB_NAME" -tAc "SELECT pg_size_pretty(pg_database_size('$ARFA_DB_NAME'))" | tr -d ' ')"
fi

# nginx
if [ "$NM" = "host" ]; then
    tgt="$(state_get nginx_target)"
    [ -n "$tgt" ] && [ -f "$tgt" ] && good "nginx drop-in: $tgt" || bad "nginx drop-in missing (${tgt:-not installed})"
    nginx -t >/dev/null 2>&1 && good "nginx -t OK" || bad "nginx -t FAILS"
elif [ "$NM" = "container" ]; then
    ncid="$(dc ps -q "nginx_${MODE:-trial}" 2>/dev/null | head -1)"
    nst="$( [ -n "$ncid" ] && docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$ncid" || echo missing)"
    [ "$nst" = "healthy" ] && good "nginx container nginx_${MODE}: $nst" || bad "nginx container nginx_${MODE}: $nst"
fi

AUTH=(); [ "$ARFA_TRIAL_AUTH" = "1" ] && [ -n "$ARFA_TRIAL_AUTH_PASSWORD" ] && AUTH=(-u "$ARFA_TRIAL_AUTH_USER:$ARFA_TRIAL_AUTH_PASSWORD")
if [ "$MODE" = "trial" ] || [ "$ARFA_KEEP_TRIAL_AFTER_DOMAIN" = "1" ]; then
    h="$(curl -s -D - -o /dev/null --max-time 15 "${AUTH[@]}" "http://127.0.0.1:$ARFA_TRIAL_PORT/" || true)"
    c="$(awk 'NR==1 {print $2}' <<< "$h")"
    [ "$c" = "200" ] && good "Trial $(trial_url) -> 200" || bad "Trial $(trial_url) -> ${c:-no answer}"
    grep -qi '^x-robots-tag: noindex' <<< "$h" && good "Trial sends X-Robots-Tag: noindex" || { [ "$MODE" = "trial" ] && bad "noindex header missing"; }
fi
if [ "$MODE" = "domain" ]; then
    CANON="$(canonical_host)"; TIP="${ARFA_NGINX_LISTEN_IP:-127.0.0.1}"
    c="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 --resolve "$CANON:443:$TIP" "https://$CANON/" || true)"
    [ "$c" = "200" ] && good "https://$CANON -> 200" || bad "https://$CANON -> $c"
    pem="/etc/letsencrypt/live/$ARFA_DOMAIN/fullchain.pem"
    if [ -f "$pem" ]; then
        end="$(openssl x509 -noout -enddate -in "$pem" | cut -d= -f2)"
        openssl x509 -checkend 1209600 -noout -in "$pem" >/dev/null && good "Certificate valid until $end" || bad "Certificate expires soon: $end"
    else bad "Certificate missing: $pem"; fi
fi

# backups / resources
lb="$(find "$ARFA_BACKUP_DIR" -maxdepth 1 -name "${ARFA_DB_NAME}_*.dump" -printf '%T@ %TY-%Tm-%Td %TH:%TM %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)"
if [ -n "$lb" ]; then
    age=$(( ( $(date +%s) - $(stat -c %Y "$(awk '{print $3}' <<< "$lb")") ) / 3600 ))
    [ "$age" -le 30 ] && good "Last backup: $lb (${age}h ago)" || note "Last backup: $lb (${age}h ago - older than 30h)"
else note "No backups yet in $ARFA_BACKUP_DIR"; fi
[ -f /etc/cron.d/arfa_prod_backup ] && good "Backup cron: /etc/cron.d/arfa_prod_backup" || note "Backup cron not installed (./backup.sh --install-cron)"
note "Volumes: $(docker system df -v 2>/dev/null | awk '/^arfa_prod_/ {printf "%s=%s ", $1, $NF}' || true)"
note "Disk free (backups): $(df -Ph "$ARFA_BACKUP_DIR" 2>/dev/null | awk 'NR==2 {print $4}')"
mapfile -t IDS < <(dc ps -q 2>/dev/null || true)
[ "${#IDS[@]}" -gt 0 ] && [ -n "${IDS[0]}" ] && { docker stats --no-stream --format '       {{.Name}}  CPU {{.CPUPerc}}  MEM {{.MemUsage}}' "${IDS[@]}" 2>/dev/null || true; }

[ "$LOGS" = 1 ] && dc logs --tail 40 odoo
printf '\n'
if [ "$BAD" -gt 0 ]; then printf '%s%d problem(s) / مشاكل%s\n' "$C_R" "$BAD" "$C_0"; exit 1; fi
printf '%sAll good / كل شيء يعمل%s\n' "$C_G" "$C_0"
