#!/usr/bin/env bash
# 51_rollback_domain.sh - arfa-sa.com back to the OLD site (restores the saved nginx file).
# إرجاع الدومين للموقع القديم.
. "$(dirname "$0")/lib.sh"
need_root
SITE=/etc/nginx/sites-enabled/arfa-sa.conf
BK=$(cat /etc/nginx/arfa-sa.conf.last_backup 2>/dev/null) || true
[ -f "$BK" ] || die "no saved copy found" "لا توجد نسخة محفوظة"
cp -a "$(readlink -f "$SITE")" "/etc/nginx/arfa-sa.conf.new_site_$(date +%Y%m%d_%H%M)"
cp -a "$BK" "$(readlink -f "$SITE")"
nginx -t && { [ "${ARFA_TEST_NO_SYSTEMD:-0}" = 1 ] && nginx -s reload || systemctl reload nginx; } && ok "arfa-sa.com -> old site again ($BK)" "رجع الدومين للموقع القديم"
IP=$(server_ip)
psql_db -q <<SQL
UPDATE ir_config_parameter SET value='http://${IP:-SERVER_IP}:$TRIAL_PORT', write_date=now() WHERE key='web.base.url';
UPDATE ir_config_parameter SET value='True', write_date=now() WHERE key='wasm_website.hide_from_search_engines';
UPDATE website SET domain=NULL;
SQL
[ "${ARFA_TEST_NO_SYSTEMD:-0}" = 1 ] || systemctl restart "$SERVICE"; ok "new site back in trial mode on port $TRIAL_PORT" "الموقع الجديد رجع لوضع التجربة"
