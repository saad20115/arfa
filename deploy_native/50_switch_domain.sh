#!/usr/bin/env bash
# 50_switch_domain.sh - AFTER the client approves: arfa-sa.com shows the NEW site.
# بعد موافقة العميل: يجعل arfa-sa.com يعرض الموقع الجديد. الموقع القديم يبقى شغالاً للرجوع إليه.
# Only /etc/nginx/sites-enabled/arfa-sa.conf is changed (a copy is kept); rollback: ./51_rollback_domain.sh
. "$(dirname "$0")/lib.sh"
need_root
SITE=/etc/nginx/sites-enabled/arfa-sa.conf
[ -f "$SITE" ] || die "$SITE not found" "ملف الدومين غير موجود"
[ "${ARFA_TEST_NO_SYSTEMD:-0}" = 1 ] || systemctl is-active -q "$SERVICE" || die "service $SERVICE is not running" "الخدمة الجديدة لا تعمل"
grep -q "127.0.0.1:$HTTP_PORT" "$SITE" && die "arfa-sa.com already points to the new site" "الدومين محوّل مسبقاً"
confirm "Switch arfa-sa.com to the NEW website now?" || die "aborted" "تم الإلغاء"
ts=$(date +%Y%m%d_%H%M)
BK="/etc/nginx/arfa-sa.conf.before_new_site_$ts"
cp -a "$(readlink -f "$SITE")" "$BK"; echo "$BK" > /etc/nginx/arfa-sa.conf.last_backup
ok "copy of the current file: $BK" "تم حفظ نسخة من الإعداد الحالي"
python3 - "$SITE" "$HTTP_PORT" "$CHAT_PORT" <<'PY'
import re, sys
path, http, chat = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(path).read()
s = s.replace('127.0.0.1:8069', '127.0.0.1:' + http).replace('127.0.0.1:8072', '127.0.0.1:' + chat)
# Odoo (proxy_mode) needs X-Forwarded-Host to trust the forwarded client IP / scheme
s = re.sub(r'(\n(\s*)proxy_set_header Host \$host;)', r'\1\n\2proxy_set_header X-Forwarded-Host $host;', s)
block = ('\n    # ARFA new site: never public\n'
         '    location ^~ /web/database { return 404; }\n'
         '    location ^~ /website/info { return 404; }\n'
         '    location ^~ /xmlrpc { return 403; }\n'
         '    location ^~ /jsonrpc { return 403; }\n'
         '    add_header X-Content-Type-Options "nosniff" always;\n'
         '    add_header Referrer-Policy "strict-origin-when-cross-origin" always;\n')
s = re.sub(r'(\n\s*client_max_body_size [^;]+;)', lambda m: m.group(1) + block, s, count=1)
open(path, 'w').write(s)
PY
if nginx -t 2>/tmp/arfa_nginx_t; then { [ "${ARFA_TEST_NO_SYSTEMD:-0}" = 1 ] && nginx -s reload || systemctl reload nginx; }; sleep 2; ok "nginx: arfa-sa.com -> new site" "تم تحويل الدومين"
else cp -a "$BK" "$(readlink -f "$SITE")"; cat /tmp/arfa_nginx_t; die "nginx test failed - original file restored" "خطأ - تمت إعادة الإعداد الأصلي"; fi
psql_db -q <<SQL
UPDATE ir_config_parameter SET value='https://arfa-sa.com', write_date=now() WHERE key='web.base.url';
UPDATE ir_config_parameter SET value='False', write_date=now() WHERE key='wasm_website.hide_from_search_engines';
UPDATE website SET domain='https://arfa-sa.com';
DELETE FROM ir_attachment WHERE url LIKE '/sitemap%.xml';
SQL
if [ "${ARFA_TEST_NO_SYSTEMD:-0}" = 1 ]; then nginx -s reload; else systemctl restart "$SERVICE"; fi; sleep 5
code=$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' -m 20 --resolve arfa-sa.com:443:127.0.0.1 https://arfa-sa.com/)
[ "$code" = 200 ] && ok "https://arfa-sa.com answers HTTP $code with the new site" "الدومين يعرض الموقع الجديد" || warn "https://arfa-sa.com answered HTTP $code - check, or run ./51_rollback_domain.sh" "تحقق أو تراجع"
echo "Search engines: allowed again. Submit https://arfa-sa.com/sitemap.xml in Google Search Console."
echo "Rollback | للرجوع للموقع القديم: sudo ./51_rollback_domain.sh"
