#!/usr/bin/env bash
# 90_remove.sh - stop and disable the new ARFA site (trial link + service). Data is KEPT unless --purge.
# إيقاف الموقع الجديد. البيانات تبقى إلا مع --purge (بعد نسخة احتياطية).
. "$(dirname "$0")/lib.sh"
need_root
grep -qs "127.0.0.1:$HTTP_PORT" /etc/nginx/sites-enabled/arfa-sa.conf && die "arfa-sa.com points to the new site - run ./51_rollback_domain.sh first" "أرجع الدومين أولاً"
confirm "Stop the new ARFA site?" || exit 1
rm -f "$NGINX_LINK"; nginx -t && systemctl reload nginx
systemctl disable -q --now "$SERVICE" 2>/dev/null || true
ok "service stopped, trial link removed" "تم الإيقاف"
if [ "${1:-}" = "--purge" ]; then
  "$KIT_DIR/20_backup.sh"
  confirm "DELETE database $DB_NAME and $DATA_DIR (a backup was just taken)?" || exit 0
  psql_su -qc "DROP DATABASE IF EXISTS \"$DB_NAME\""; rm -rf "$DATA_DIR" "$UNIT" "$NGINX_SITE" "$HTPASSWD"; systemctl daemon-reload
  ok "database and files removed (backup in $BACKUP_DIR)" "تم الحذف"
fi
