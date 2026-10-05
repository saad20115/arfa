#!/usr/bin/env bash
# =============================================================================
# backup.sh - database (pg_dump -Fc) + filestore (tar.gz) of ARFA, with retention.
# نسخ احتياطي لقاعدة البيانات والملفات مع حذف النسخ القديمة تلقائياً.
#
# Usage: sudo ./backup.sh [--dest DIR] [--keep-days N] [--tag NAME] [--quiet]
#        sudo ./backup.sh --install-cron   # daily 03:17 via /etc/cron.d/arfa_prod_backup
#        sudo ./backup.sh --remove-cron
# Output: <dest>/arfa_prod_<YYYYmmdd_HHMMSS>[_tag].dump
#         <dest>/arfa_prod_<YYYYmmdd_HHMMSS>[_tag]_filestore.tar.gz   (top folder: arfa_prod/)
#         <dest>/arfa_prod_<YYYYmmdd_HHMMSS>[_tag].sha256
# Only files named arfa_prod_* in <dest> are ever deleted; the newest 3 sets are always kept.
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"

DEST=""; KEEP=""; TAG=""; QUIET=0; CRON=""
need_root; require_docker; require_env_file; load_env
while [ $# -gt 0 ]; do
    case "$1" in
        --dest) DEST="$2"; shift 2;;
        --keep-days) KEEP="$2"; shift 2;;
        --tag) TAG="$(tr -cd 'A-Za-z0-9-' <<< "$2")"; shift 2;;
        --quiet) QUIET=1; shift;;
        --install-cron) CRON=install; shift;;
        --remove-cron) CRON=remove; shift;;
        -h|--help) sed -n '2,15p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done
DEST="${DEST:-$ARFA_BACKUP_DIR}"; KEEP="${KEEP:-$ARFA_BACKUP_KEEP_DAYS}"
CRON_FILE=/etc/cron.d/arfa_prod_backup
CRON_LINE="17 3 * * * root $KIT_DIR/backup.sh --quiet >> /var/log/arfa_prod_backup.log 2>&1"

if [ "$CRON" = "install" ]; then
    printf '%s\n# daily ARFA backup (db + filestore), keeps %s days\nSHELL=/bin/bash\nPATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n%s\n' \
        "$KIT_MARKER" "$KEEP" "$CRON_LINE" > "$CRON_FILE"
    chmod 644 "$CRON_FILE"
    ok "Installed $CRON_FILE:" "تم تفعيل النسخ الاحتياطي اليومي:"; echo "    $CRON_LINE"; exit 0
fi
if [ "$CRON" = "remove" ]; then
    if [ -f "$CRON_FILE" ] && grep -q "$KIT_MARKER" "$CRON_FILE"; then rm -f "$CRON_FILE"; ok "Removed $CRON_FILE" "تم إلغاء الجدولة"; fi
    exit 0
fi

log() { [ "$QUIET" = 1 ] && printf '%s %s\n' "$(date '+%F %T')" "$1" || info "$1" "${2:-}"; }

mkdir -p "$DEST" "$RUNTIME_DIR"; chmod 700 "$DEST"
exec 9>"$RUNTIME_DIR/backup.lock"
flock -n 9 || die "Another backup is running" "يوجد نسخ احتياطي آخر قيد التشغيل"

wait_healthy db 60 || { dc up -d db; wait_healthy db 120 || die "PostgreSQL not running" "قاعدة البيانات لا تعمل"; }
db_exists || die "Database $ARFA_DB_NAME does not exist" "قاعدة البيانات غير موجودة"

NAME="${ARFA_DB_NAME}_$(ts_now)${TAG:+_$TAG}"
DUMP="$DEST/$NAME.dump"; FS="$DEST/${NAME}_filestore.tar.gz"
avail="$(df -Pm "$DEST" | awk 'NR==2 {print $4}')"
[ "$avail" -gt 1024 ] || die "Less than 1 GB free in $DEST" "المساحة الحرة أقل من 1 جيجا"

log "Dumping database $ARFA_DB_NAME -> $DUMP" "نسخ قاعدة البيانات"
if ! dc exec -T db pg_dump -U "$ARFA_DB_USER" -Fc -Z 6 "$ARFA_DB_NAME" > "$DUMP.part"; then
    rm -f "$DUMP.part"; die "pg_dump failed" "فشل نسخ قاعدة البيانات"
fi
dc exec -T db pg_restore -l < "$DUMP.part" > /dev/null || { rm -f "$DUMP.part"; die "Dump verification failed" "فشل التحقق من النسخة"; }
mv "$DUMP.part" "$DUMP"

log "Archiving filestore -> $FS" "أرشفة الملفات"
# shellcheck disable=SC2016
if ! dc run --rm -T --no-deps --user 0 --entrypoint bash odoo -c \
    'cd /var/lib/odoo/filestore 2>/dev/null && [ -d "$1" ] || { mkdir -p /tmp/e/"$1"; cd /tmp/e; }; tar -czf - "$1"' _ "$ARFA_DB_NAME" > "$FS.part"; then
    rm -f "$FS.part" "$DUMP"; die "filestore archive failed" "فشلت أرشفة الملفات"
fi
gzip -t "$FS.part" || { rm -f "$FS.part" "$DUMP"; die "filestore archive is corrupt" "الأرشيف تالف"; }
mv "$FS.part" "$FS"
( cd "$DEST" && sha256sum "$(basename "$DUMP")" "$(basename "$FS")" > "$NAME.sha256" )
chmod 600 "$DUMP" "$FS" "$DEST/$NAME.sha256"

# ------------------------------------------------------------- retention ----
mapfile -t SETS < <(find "$DEST" -maxdepth 1 -type f -name "${ARFA_DB_NAME}_*.dump" -printf '%T@ %p\n' | sort -rn | cut -d' ' -f2-)
removed=0; i=0
for d in "${SETS[@]}"; do
    i=$((i+1)); [ "$i" -le 3 ] && continue
    if [ -n "$(find "$d" -mtime +"$KEEP" -print)" ]; then
        b="${d%.dump}"; rm -f "$d" "${b}_filestore.tar.gz" "$b.sha256"; removed=$((removed+1))
    fi
done
log "Backup OK: $(du -h "$DUMP" | cut -f1) db + $(du -h "$FS" | cut -f1) files; removed $removed old set(s) (> $KEEP days)" "تم النسخ الاحتياطي بنجاح"
[ "$QUIET" = 1 ] || printf '\nRestore with / للاستعادة:\n  sudo %s/restore.sh --dump %s --filestore %s\nCron line / سطر الجدولة:\n  %s\n  (install it with: sudo %s/backup.sh --install-cron)\n' \
    "$KIT_DIR" "$DUMP" "$FS" "$CRON_LINE" "$KIT_DIR"
printf '%s\n' "$NAME" > "$RUNTIME_DIR/last_backup"
