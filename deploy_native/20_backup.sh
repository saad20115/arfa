#!/usr/bin/env bash
# 20_backup.sh - backup of the new ARFA site (database + files) into $BACKUP_DIR, keeps the last 14 days.
# نسخة احتياطية لقاعدة بيانات وملفات موقع عرفة الجديد. للجدولة اليومية: sudo ./20_backup.sh --install-cron
. "$(dirname "$0")/lib.sh"
need_root
if [ "${1:-}" = "--install-cron" ]; then
  echo "30 2 * * * root $KIT_DIR/20_backup.sh >> $LOG_DIR/backup.log 2>&1" > /etc/cron.d/arfa_backup
  ok "daily backup at 02:30 -> /etc/cron.d/arfa_backup" "تمت جدولة النسخ اليومي"; exit 0; fi
db_exists || die "database $DB_NAME not found" "القاعدة غير موجودة"
ts=$(date +%Y%m%d_%H%M); dest="$BACKUP_DIR/$ts"; install -d -m 700 "$dest"
as_pg pg_dump -Fc -d "$DB_NAME" -f /tmp/arfa_bk.dump && mv /tmp/arfa_bk.dump "$dest/$DB_NAME.dump"
[ -d "$DATA_DIR/filestore/$DB_NAME" ] && tar -C "$DATA_DIR/filestore" -czf "$dest/${DB_NAME}_filestore.tar.gz" "$DB_NAME"
(cd "$dest" && sha256sum ./* > SHA256SUMS)
find "$BACKUP_DIR" -mindepth 1 -maxdepth 1 -type d -name '20*' -mtime +14 -exec rm -rf {} +
ok "backup: $dest ($(du -sh "$dest" | cut -f1))" "تم النسخ الاحتياطي"
