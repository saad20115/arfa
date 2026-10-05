#!/usr/bin/env bash
# 40_status.sh - health of the new ARFA site (read-only). حالة موقع عرفة الجديد.
. "$(dirname "$0")/lib.sh"
set +e
echo "service  : $(systemctl is-active "$SERVICE") ($(systemctl is-enabled "$SERVICE" 2>/dev/null))"
echo "odoo     : HTTP $(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://127.0.0.1:$HTTP_PORT/")  on 127.0.0.1:$HTTP_PORT"
echo "trial    : nginx site $( [ -L "$NGINX_LINK" ] && echo enabled || echo disabled ) on port $TRIAL_PORT"
echo "domain   : arfa-sa.com -> $(grep -oE 'proxy_pass http://127.0.0.1:[0-9]+' /etc/nginx/sites-enabled/arfa-sa.conf 2>/dev/null | sort -u | tr '\n' ' ')"
echo "module   : wasm_website $(psql_db -Atc "select latest_version from ir_module_module where name='wasm_website'" 2>/dev/null)"
echo "base url : $(psql_db -Atc "select value from ir_config_parameter where key='web.base.url'" 2>/dev/null)"
echo "noindex  : $(psql_db -Atc "select value from ir_config_parameter where key='wasm_website.hide_from_search_engines'" 2>/dev/null)"
echo "mail srv : $(psql_db -Atc "select count(*) from ir_mail_server where active" 2>/dev/null) outgoing server(s) configured"
echo "backups  : $(ls -1d "$BACKUP_DIR"/20* 2>/dev/null | tail -1) (cron: $( [ -f /etc/cron.d/arfa_backup ] && echo yes || echo no))"
echo "disk     : db $(psql_su -Atc "select pg_size_pretty(pg_database_size('$DB_NAME'))" 2>/dev/null), files $(du -sh "$DATA_DIR/filestore/$DB_NAME" 2>/dev/null | cut -f1)"
echo "errors   : $(grep -c ' ERROR ' "$LOG_DIR/arfa.log" 2>/dev/null || true) ERROR lines in $LOG_DIR/arfa.log"
