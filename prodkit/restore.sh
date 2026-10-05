#!/usr/bin/env bash
# =============================================================================
# restore.sh - restore ARFA from a backup set (this kit's backup.sh, or a copy
# from the developer PC: <db>.dump + filestore folder or .tar.gz).
# استعادة الموقع من نسخة احتياطية (يأخذ نسخة أمان من الوضع الحالي أولاً).
#
# Usage: sudo ./restore.sh --list
#        sudo ./restore.sh --latest
#        sudo ./restore.sh --set arfa_prod_20261005_031700           # name from --list
#        sudo ./restore.sh --dump FILE.dump --filestore DIR|FILE.tar.gz
#        sudo ./restore.sh --from DIR                                 # folder with .dump + filestore
# Options: --no-safety-backup   --yes   --no-upgrade (skip "-u modules" after restore)
# The current phase (trial/domain) is re-applied: web.base.url, noindex, website domain.
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"

DUMP=""; FILESTORE=""; SET=""; LIST=0; LATEST=0; SAFETY=1; UPGRADE=1; FROM=""
need_root; require_docker; require_env_file; load_env
while [ $# -gt 0 ]; do
    case "$1" in
        --list) LIST=1; shift;;
        --latest) LATEST=1; shift;;
        --set) SET="$2"; shift 2;;
        --dump) DUMP="$2"; shift 2;;
        --filestore) FILESTORE="$2"; shift 2;;
        --from) FROM="$2"; shift 2;;
        --no-safety-backup) SAFETY=0; shift;;
        --no-upgrade) UPGRADE=0; shift;;
        -y|--yes) export ARFA_ASSUME_YES=1; shift;;
        -h|--help) sed -n '2,16p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done

list_sets() {
    find "$ARFA_BACKUP_DIR" -maxdepth 1 -type f -name "${ARFA_DB_NAME}_*.dump" -printf '%T@ %p\n' 2>/dev/null | sort -rn | cut -d' ' -f2-
}
if [ "$LIST" = 1 ]; then
    printf 'Backups in %s (newest first) / النسخ المتاحة:\n' "$ARFA_BACKUP_DIR"
    while read -r d; do
        [ -n "$d" ] || continue
        b="${d%.dump}"; printf '  %-48s db %-6s files %s\n' "$(basename "$b")" "$(du -h "$d" | cut -f1)" \
            "$( [ -f "${b}_filestore.tar.gz" ] && du -h "${b}_filestore.tar.gz" | cut -f1 || echo MISSING)"
    done < <(list_sets)
    exit 0
fi

if [ "$LATEST" = 1 ]; then   # newest COMPLETE set (dump + filestore archive)
    while read -r d; do
        [ -n "$d" ] && [ -f "${d%.dump}_filestore.tar.gz" ] && { SET="$(basename "$d" .dump)"; break; }
    done < <(list_sets)
    [ -n "$SET" ] || die "No complete backup set found in $ARFA_BACKUP_DIR" "لا توجد نسخة كاملة"
fi
if [ -n "$SET" ]; then
    DUMP="$ARFA_BACKUP_DIR/$SET.dump"; FILESTORE="$ARFA_BACKUP_DIR/${SET}_filestore.tar.gz"
    if [ -f "$ARFA_BACKUP_DIR/$SET.sha256" ]; then
        ( cd "$ARFA_BACKUP_DIR" && sha256sum -c --quiet "$SET.sha256" ) || die "Checksum mismatch for $SET" "النسخة تالفة (checksum)"
        ok "Checksums OK" "التحقق من سلامة النسخة ناجح"
    fi
fi
if [ -n "$FROM" ]; then
    [ -n "$DUMP" ] || DUMP="$(find_dump_in "$FROM")"
    [ -n "$FILESTORE" ] || FILESTORE="$(find_filestore_in "$FROM")"
fi
[ -n "$DUMP" ] && [ -f "$DUMP" ] || die "Give --latest, --set NAME, --from DIR or --dump FILE (see --list)" "حدد النسخة المطلوبة (راجع --list)"
[ -n "$FILESTORE" ] || FILESTORE="$(find_filestore_for "$DUMP")"
[ -n "$FILESTORE" ] && [ -e "$FILESTORE" ] || die "Filestore not found for $DUMP (use --filestore)" "ملفات الموقع غير موجودة - استخدم --filestore"
DUMP="$(readlink -f "$DUMP")"; FILESTORE="$(readlink -f "$FILESTORE")"

info "Restore database : $DUMP" "ملف قاعدة البيانات"
info "Restore files    : $FILESTORE" "ملفات الموقع"
confirm "This REPLACES the live database '$ARFA_DB_NAME' and its files. Continue?" \
        "سيتم استبدال قاعدة البيانات الحالية وملفاتها بالكامل. هل تريد المتابعة؟" || die "Aborted." "تم الإلغاء."

wait_healthy db 60 || { dc up -d db; wait_healthy db 120 || die "PostgreSQL not running" "قاعدة البيانات لا تعمل"; }
if db_exists && [ "$SAFETY" = 1 ]; then
    step "Safety backup of the current state" "نسخة أمان من الوضع الحالي"
    "$KIT_DIR/backup.sh" --tag pre-restore
fi

step "Restoring" "جاري الاستعادة"
dc stop odoo >/dev/null 2>&1 || true
db_exists && drop_db
restore_db "$DUMP"
restore_filestore "$FILESTORE"
if [ "$UPGRADE" = 1 ]; then
    odoo_update "$ARFA_UPDATE_MODULES" || warn "Module upgrade reported errors - site may still work; check the log" "ظهرت أخطاء في تحديث الموديولات"
fi
MODE="$(state_get mode)"; [ -n "$MODE" ] || MODE=trial
apply_mode_params "$MODE"
dc up -d odoo
wait_healthy odoo 300 || { dc logs --tail 60 odoo >&2; die "Odoo is not healthy after restore" "أودو لم يعمل بعد الاستعادة"; }
ok "Restore complete ($MODE mode)" "تمت الاستعادة بنجاح"
printf 'Undo / للتراجع:  sudo %s/restore.sh --list   then --set <the *_pre-restore set>\n' "$KIT_DIR"
