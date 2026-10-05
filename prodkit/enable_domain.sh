#!/usr/bin/env bash
# =============================================================================
# enable_domain.sh - Phase 2: serve ARFA on https://arfa-sa.com (+ www) with a
# Let's Encrypt certificate, HTTP->HTTPS, www<->apex redirect, noindex removed.
# المرحلة الثانية: تشغيل الموقع على النطاق مع شهادة HTTPS مجانية وإلغاء الإخفاء عن محركات البحث.
#
# Usage: sudo ./enable_domain.sh [--domain arfa-sa.com] [--canonical apex|www] [--email you@x.com]
#                                [--hsts|--no-hsts] [--keep-trial|--no-keep-trial]
#                                [--dry-run] [--skip-dns-check] [--renew]
#   --dry-run   only test certificate issuance (certbot --dry-run), change nothing permanent
#   --hsts      add Strict-Transport-Security (only after HTTPS is confirmed working!)
#   --renew     force a new certificate even if the current one is valid
# Re-running is safe (cert is reused while valid > 30 days).
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"
. "$(dirname "$0")/lib/nginx.sh"

DRY=0; SKIP_DNS=0; RENEW=0
need_root; require_docker; require_env_file; load_env
while [ $# -gt 0 ]; do
    case "$1" in
        --domain) set_env ARFA_DOMAIN "$2"; shift 2;;
        --canonical) [[ "$2" =~ ^(apex|www)$ ]] || die "--canonical apex|www"; set_env ARFA_CANONICAL "$2"; shift 2;;
        --email) set_env ARFA_LE_EMAIL "$2"; shift 2;;
        --hsts) set_env ARFA_HSTS 1; shift;;
        --no-hsts) set_env ARFA_HSTS 0; shift;;
        --keep-trial) set_env ARFA_KEEP_TRIAL_AFTER_DOMAIN 1; shift;;
        --no-keep-trial) set_env ARFA_KEEP_TRIAL_AFTER_DOMAIN 0; shift;;
        --dry-run) DRY=1; shift;;
        --skip-dns-check) SKIP_DNS=1; shift;;
        --renew) RENEW=1; shift;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done

APEX="$ARFA_DOMAIN"; WWW="www.$ARFA_DOMAIN"; CANON="$(canonical_host)"
MODE="$(nginx_mode)"; state_set nginx_mode "$MODE"
PREV_MODE="$(state_get mode)"; [ -n "$PREV_MODE" ] || PREV_MODE=trial
KEEP="$ARFA_KEEP_TRIAL_AFTER_DOMAIN"
if [ "$MODE" = "container" ] && [ "$KEEP" = "1" ]; then
    warn "--keep-trial is only supported with host nginx - ignored" "الإبقاء على رابط التجربة متاح فقط مع nginx المضيف"; KEEP=0
fi
CERT_DIR="/etc/letsencrypt/live/$APEX"
step "Domain $APEX / $WWW -> canonical https://$CANON (nginx: $MODE)" "تفعيل النطاق"

# -------------------------------------------------------------------- DNS ----
if [ "$SKIP_DNS" = 0 ]; then
    for h in "$APEX" "$WWW"; do
        r="$(getent ahostsv4 "$h" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ' || true)"
        grep -qw "$ARFA_PUBLIC_IP" <<< "$r" || die "DNS: $h -> '${r:-nothing}', expected $ARFA_PUBLIC_IP. Add an A record and wait." \
            "النطاق $h لا يشير إلى هذا الخادم ($ARFA_PUBLIC_IP). أضف سجل A عند مزوّد النطاق وانتظر الانتشار."
        ok "DNS $h -> $r" "النطاق يشير إلى الخادم"
    done
fi

# ------------------------------------------------- conflicts with others ----
if [ "$MODE" = "host" ]; then
    others="$(nginx_dump_others)"
    if grep -Eq "^[^#]*server_name[^;]*[[:space:]](www\.)?${APEX//./\\.}[[:space:];]" <<< "$others"; then
        die "Another nginx vhost already declares server_name $APEX - remove/disable it first (nginx -T | grep -n $APEX)." \
            "يوجد موقع آخر في nginx يستخدم نفس النطاق - عطّله أولاً."
    fi
else
    for p in 80 443; do
        l="$(ss -H -ltnp "sport = :$p" 2>/dev/null || true)"
        if [ -n "$l" ] && ! grep -q "docker-proxy" <<< "$l"; then die "Port $p is used by: $l" "المنفذ $p مستخدم من برنامج آخر"; fi
        if [ -n "$l" ] && ! grep -q ":$p->" <<< "$(dc ps --format '{{.Ports}}' 2>/dev/null || true)"; then
            die "Port $p is published by another container - add $APEX to that proxy instead." "المنفذ $p تستخدمه حاوية أخرى"
        fi
    done
fi

# ---------------------------------------------------------------- certbot ----
if ! have certbot; then
    step "Installing certbot" "تثبيت certbot"
    if have apt-get; then DEBIAN_FRONTEND=noninteractive apt-get install -y -qq certbot
    elif have dnf; then dnf install -y -q certbot
    else die "Install certbot manually (snap install --classic certbot)" "ثبّت certbot يدوياً"; fi
fi
mkdir -p "$ARFA_ACME_WEBROOT/.well-known/acme-challenge"; chmod 755 "$ARFA_ACME_WEBROOT" "$ARFA_ACME_WEBROOT/.well-known" "$ARFA_ACME_WEBROOT/.well-known/acme-challenge"

cert_ok() {
    [ -f "$CERT_DIR/fullchain.pem" ] || return 1
    openssl x509 -checkend 2592000 -noout -in "$CERT_DIR/fullchain.pem" >/dev/null 2>&1 || return 1
    local san; san="$(openssl x509 -noout -ext subjectAltName -in "$CERT_DIR/fullchain.pem" 2>/dev/null || true)"
    grep -q "DNS:$APEX" <<< "$san" && grep -q "DNS:$WWW" <<< "$san"
}

restore_previous() {
    warn "Restoring the previous nginx layout ($PREV_MODE)" "إعادة إعدادات nginx السابقة"
    if [ "$PREV_MODE" = "domain" ] && cert_ok; then
        install_nginx_conf domain "$KEEP"; [ "$MODE" = "container" ] && start_nginx_container domain
    else
        install_nginx_conf trial 0; [ "$MODE" = "container" ] && start_nginx_container trial
        state_set mode trial
    fi
    return 0
}

if [ "$RENEW" = 1 ] || [ "$DRY" = 1 ] || ! cert_ok; then
    step "ACME challenge via nginx (webroot $ARFA_ACME_WEBROOT)" "تجهيز التحقق من النطاق"
    if [ "$PREV_MODE" = "domain" ] && cert_ok; then
        :   # current domain layout already serves /.well-known/acme-challenge/
    else
        install_nginx_conf acme "$( [ "$MODE" = host ] && echo 1 || echo 0 )"   # host: trial stays up meanwhile
        if [ "$MODE" = "container" ]; then start_nginx_container domain; fi
    fi
    tok="arfa-selftest-$(gen_secret 6)"
    printf 'ok-%s\n' "$tok" > "$ARFA_ACME_WEBROOT/.well-known/acme-challenge/$tok"
    sleep 1
    got="$(curl -s --max-time 10 "http://$APEX/.well-known/acme-challenge/$tok" || true)"
    rm -f "$ARFA_ACME_WEBROOT/.well-known/acme-challenge/$tok"
    if [ "$got" = "ok-$tok" ]; then ok "http://$APEX/.well-known/acme-challenge/ reachable" "مسار التحقق يعمل"
    else warn "ACME self-test failed (got '${got:0:60}') - certbot will probably fail (firewall port 80? DNS?)" "اختبار التحقق فشل - تأكد من فتح المنفذ 80"; fi

    CB=(certbot certonly --webroot -w "$ARFA_ACME_WEBROOT" -d "$APEX" -d "$WWW" --cert-name "$APEX"
        --non-interactive --agree-tos --keep-until-expiring --deploy-hook "$(nginx_reload_cmd)")
    if [ -n "$ARFA_LE_EMAIL" ]; then CB+=(--email "$ARFA_LE_EMAIL"); else CB+=(--register-unsafely-without-email); fi
    [ "$RENEW" = 1 ] && CB+=(--force-renewal)
    [ "$DRY" = 1 ] && CB+=(--dry-run)
    step "Requesting certificate: ${CB[*]}" "طلب شهادة HTTPS"
    if ! "${CB[@]}"; then
        restore_previous
        die "certbot failed - previous configuration restored (site still on the trial link)." "فشل إصدار الشهادة - تمت إعادة الإعدادات السابقة."
    fi
    if [ "$DRY" = 1 ]; then
        restore_previous
        ok "Dry run OK - certificate issuance works. Run again without --dry-run." "الاختبار ناجح - أعد التشغيل بدون --dry-run"
        exit 0
    fi
fi
cert_ok || die "Certificate missing in $CERT_DIR" "الشهادة غير موجودة"
ok "Certificate: $(openssl x509 -noout -enddate -in "$CERT_DIR/fullchain.pem")" "الشهادة صالحة"

# --------------------------------------------------------- final layout ----
step "Installing HTTPS server blocks" "تركيب إعدادات HTTPS"
install_nginx_conf domain "$KEEP"
if [ "$MODE" = "container" ]; then start_nginx_container domain; fi
state_set mode domain

step "Odoo: base URL https://$CANON, website domain, search engines allowed" "ضبط رابط أودو وإظهار الموقع لمحركات البحث"
apply_mode_params domain
dc restart odoo >/dev/null
wait_healthy odoo 300 || die "Odoo not healthy after restart" "أودو لم يعمل بعد إعادة التشغيل"

# ---------------------------------------------------------------- verify ----
step "Self-test" "اختبار ذاتي"
TIP="${ARFA_NGINX_LISTEN_IP:-127.0.0.1}"
R=(--resolve "$APEX:80:$TIP" --resolve "$WWW:80:$TIP" --resolve "$APEX:443:$TIP" --resolve "$WWW:443:$TIP")
fails=0
t() { if [ "$2" = "$3" ]; then ok "$1" "$3"; else err "$1: got '$3' expected '$2'" ""; fails=$((fails+1)); fi; }
h="$(curl -s -D - -o /dev/null "${R[@]}" "https://$CANON/" || true)"
t "https://$CANON/ status" "200" "$(awk 'NR==1 {print $2}' <<< "$h")"
t "no X-Robots-Tag on https://$CANON" "0" "$(grep -ci '^x-robots-tag' <<< "$h" || true)"
t "http://$APEX -> https://$CANON/" "https://$CANON/" "$(curl -s -o /dev/null -w '%{redirect_url}' "${R[@]}" "http://$APEX/" || true)"
OTHER="$APEX"; [ "$CANON" = "$APEX" ] && OTHER="$WWW"
t "https://$OTHER -> https://$CANON/" "https://$CANON/" "$(curl -s -o /dev/null -w '%{redirect_url}' "${R[@]}" "https://$OTHER/" || true)"
t "/web/database/manager blocked" "404" "$(curl -s -o /dev/null -w '%{http_code}' "${R[@]}" "https://$CANON/web/database/manager" || true)"
if [ "$ARFA_HSTS" = "1" ]; then t "HSTS header" "1" "$(grep -ci '^strict-transport-security' <<< "$h" || true)"; fi

cat <<EOF

${C_G}ARFA is live / الموقع يعمل الآن:${C_0} https://$CANON
  - Odoo > Website > Configuration > Settings > Domain = https://$CANON (set automatically when there is one website)
    أودو ← الموقع ← الإعدادات ← حقل النطاق (Domain) = https://$CANON
  - Certificate renews automatically (certbot timer) and nginx reloads via deploy-hook.
EOF
[ "$ARFA_HSTS" = "1" ] || printf '  - When HTTPS works for a few days: sudo ./enable_domain.sh --hsts\n    بعد التأكد من عمل HTTPS لعدة أيام فعّل HSTS بالأمر أعلاه.\n'
[ "$KEEP" = "1" ] && printf '  - Trial link %s still answers (noindex).\n' "$(trial_url)"
[ "$KEEP" = "1" ] || printf '  - The trial port %s is closed now (you may: ufw delete allow %s/tcp).\n' "$ARFA_TRIAL_PORT" "$ARFA_TRIAL_PORT"
[ "$fails" -eq 0 ] || die "$fails self-test(s) failed - see above" "فشل $fails من الاختبارات"
