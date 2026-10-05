#!/usr/bin/env bash
# =============================================================================
# enable_trial_nginx.sh - Phase 1: publish ARFA on http://SERVER_IP:ARFA_TRIAL_PORT
# through nginx (host drop-in or own container), optional password, noindex.
# المرحلة الأولى: نشر الموقع على http://IP:PORT مع كلمة مرور اختيارية وإخفاء عن محركات البحث.
#
# Usage: sudo ./enable_trial_nginx.sh [--port 8090] [--user arfa] [--password X | --new-password]
#                                     [--no-auth] [--mode host|container] [--open-firewall] [--no-params]
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"
. "$(dirname "$0")/lib/nginx.sh"

OPEN_FW=0; NO_PARAMS=0; MODE_OPT=""
need_root; require_docker; require_env_file; load_env
while [ $# -gt 0 ]; do
    case "$1" in
        --port) set_env ARFA_TRIAL_PORT "$2"; shift 2;;
        --user) set_env ARFA_TRIAL_AUTH_USER "$2"; shift 2;;
        --password) set_env ARFA_TRIAL_AUTH_PASSWORD "$2"; set_env ARFA_TRIAL_AUTH 1; shift 2;;
        --new-password) set_env ARFA_TRIAL_AUTH_PASSWORD "$(gen_readable 14)"; set_env ARFA_TRIAL_AUTH 1; shift;;
        --no-auth) set_env ARFA_TRIAL_AUTH 0; shift;;
        --mode) MODE_OPT="$2"; shift 2;;
        --open-firewall) OPEN_FW=1; shift;;
        --no-params) NO_PARAMS=1; shift;;
        -h|--help) sed -n '2,10p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done
if [ "$ARFA_TRIAL_AUTH" = "1" ] && [ -z "$ARFA_TRIAL_AUTH_PASSWORD" ]; then set_env ARFA_TRIAL_AUTH_PASSWORD "$(gen_readable 14)"; fi
case "$MODE_OPT" in
    "") ;;
    host|container) state_set nginx_mode "$MODE_OPT";;
    *) die "--mode must be host or container" "يجب أن يكون الوضع host أو container";;
esac
[ "$(state_get mode)" = "domain" ] && warn "Site is in DOMAIN mode; this re-enables the trial layout (domain server blocks removed)." \
    "الموقع حالياً على النطاق؛ هذا الأمر يعيد وضع التجربة."

MODE="$(nginx_mode)"
state_set nginx_mode "$MODE"
step "nginx mode: $MODE" "وضع nginx: $MODE"
wait_healthy odoo 30 || { dc up -d odoo; wait_healthy odoo 300 || die "Odoo is not running/healthy - run install.sh" "أودو لا يعمل - شغّل install.sh"; }

# port must be free unless it is ours
l="$(ss -H -ltnp "sport = :$ARFA_TRIAL_PORT" 2>/dev/null || true)"
if [ -n "$l" ]; then
    tgt="$(state_get nginx_target)"
    if ! { [ -n "$tgt" ] && [ -f "$tgt" ] && grep -q "listen .*$ARFA_TRIAL_PORT" "$tgt"; } && \
       ! grep -q ":$ARFA_TRIAL_PORT->" <<< "$(dc ps --format '{{.Ports}}' 2>/dev/null || true)"; then
        die "Port $ARFA_TRIAL_PORT is used by another program - choose another: --port N" "المنفذ $ARFA_TRIAL_PORT مستخدم من برنامج آخر - اختر غيره عبر --port"
    fi
fi

step "Installing nginx config (trial)" "تركيب إعدادات nginx للتجربة"
install_nginx_conf trial 0
state_set mode trial
if [ "$MODE" = "container" ]; then start_nginx_container trial; fi

if [ "$NO_PARAMS" = 0 ]; then
    step "Odoo base URL + noindex switch" "رابط أودو وإخفاء الموقع"
    apply_mode_params trial
    dc restart odoo >/dev/null
    wait_healthy odoo 300 || die "Odoo not healthy after restart" "أودو لم يعمل بعد إعادة التشغيل"
fi

if [ "$OPEN_FW" = 1 ]; then
    if have ufw && grep -q 'Status: active' <<< "$(ufw status 2>/dev/null || true)"; then ufw allow "${ARFA_TRIAL_PORT}/tcp" comment 'arfa_prod trial'; fi
    if have firewall-cmd && firewall-cmd --state >/dev/null 2>&1; then firewall-cmd --permanent --add-port="${ARFA_TRIAL_PORT}/tcp" && firewall-cmd --reload; fi
fi

# ---------------------------------------------------------------- verify ----
step "Self-test through nginx" "اختبار ذاتي عبر nginx"
sleep 2
base="http://127.0.0.1:$ARFA_TRIAL_PORT"
AUTH=(); [ "$ARFA_TRIAL_AUTH" = "1" ] && AUTH=(-u "$ARFA_TRIAL_AUTH_USER:$ARFA_TRIAL_AUTH_PASSWORD")
fails=0
chk() { # chk <label> <expected-regex> <actual>
    if grep -Eq "^($2)$" <<< "$3"; then ok "$1: $3" ""; else err "$1: got '$3' (expected $2)" ""; fails=$((fails+1)); fi
}
hdrs="$(curl -s -D - -o /dev/null "${AUTH[@]}" -H "Host: ${ARFA_PUBLIC_IP}:${ARFA_TRIAL_PORT}" "$base/" || true)"
chk "Home page" "200" "$(awk 'NR==1 {print $2}' <<< "$hdrs")"
chk "X-Robots-Tag noindex" "1" "$(grep -ci '^x-robots-tag: noindex' <<< "$hdrs" || true)"
chk "/web/database/manager blocked" "404" "$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" "$base/web/database/manager" || true)"
chk "/xmlrpc/2/common blocked" "403" "$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" "$base/xmlrpc/2/common" || true)"
chk "/robots.txt Disallow" "1" "$(curl -s "${AUTH[@]}" "$base/robots.txt" | grep -c '^Disallow: /$' || true)"
if [ "$ARFA_TRIAL_AUTH" = "1" ]; then
    chk "Password required" "401" "$(curl -s -o /dev/null -w '%{http_code}' "$base/" || true)"
fi
ext="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "${AUTH[@]}" "http://${ARFA_PUBLIC_IP}:${ARFA_TRIAL_PORT}/" || true)"
[ "$ext" = "200" ] && ok "Reachable via public IP (from this server)" "يمكن الوصول عبر العنوان العام" \
    || warn "Public IP test returned '$ext' - check cloud/ufw firewall for port $ARFA_TRIAL_PORT" "تأكد من فتح المنفذ $ARFA_TRIAL_PORT في الجدار الناري"

printf '\n%sTrial link / رابط التجربة:%s %s\n' "$C_G" "$C_0" "$(trial_url)"
[ "$ARFA_TRIAL_AUTH" = "1" ] && printf '  user / المستخدم: %s\n  password / كلمة المرور: %s\n' "$ARFA_TRIAL_AUTH_USER" "$ARFA_TRIAL_AUTH_PASSWORD"
[ "$fails" -eq 0 ] || die "$fails self-test(s) failed" "فشل $fails من الاختبارات الذاتية"
