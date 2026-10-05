#!/usr/bin/env bash
# =============================================================================
# install.sh - first installation of ARFA (Odoo 19) on the VPS. Idempotent.
# التثبيت الأول لموقع عرفة. يمكن إعادة تشغيله بأمان.
#
# Usage:
#   sudo ./install.sh --from /opt/arfa/backups/2026-10-05       # folder with <db>.dump + filestore (folder or .tar.gz)
#   sudo ./install.sh --dump /opt/arfa/arfa2026_db.dump --filestore /opt/arfa/arfa2026_filestore.tar.gz
#   sudo ./install.sh                                            # re-run: re-render config, (re)start, no restore
# Options:
#   --force           replace an EXISTING arfa_prod database (a safety backup is taken first)
#   --no-nginx        do not run enable_trial_nginx.sh at the end
#   --no-auth         trial link without password (sets ARFA_TRIAL_AUTH=0)
#   --skip-preflight  do not run preflight.sh
#   -y | --yes        do not ask questions
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"

DUMP=""; FILESTORE=""; FROM=""; FORCE=0; NO_NGINX=0; NO_AUTH=0; SKIP_PF=0
while [ $# -gt 0 ]; do
    case "$1" in
        --dump) DUMP="$2"; shift 2;;
        --filestore) FILESTORE="$2"; shift 2;;
        --from) FROM="$2"; shift 2;;
        --force) FORCE=1; shift;;
        --no-nginx) NO_NGINX=1; shift;;
        --no-auth) NO_AUTH=1; shift;;
        --skip-preflight) SKIP_PF=1; shift;;
        -y|--yes) export ARFA_ASSUME_YES=1; shift;;
        -h|--help) sed -n '2,19p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done
need_root
require_docker
have openssl || die "openssl is required" "openssl مطلوب"

# ---------------------------------------------------------------- inputs ----
if [ -n "$FROM" ]; then
    [ -d "$FROM" ] || die "--from must be a folder: $FROM" "يجب أن يكون --from مجلداً"
    [ -n "$DUMP" ] || DUMP="$(find_dump_in "$FROM")"
    [ -n "$FILESTORE" ] || FILESTORE="$(find_filestore_in "$FROM")"
    [ -n "$DUMP" ] || die "No *.dump file in $FROM" "لا يوجد ملف .dump في المجلد"
fi
if [ -n "$DUMP" ]; then
    DUMP="$(readlink -f "$DUMP")"
    [ -f "$DUMP" ] || die "Dump not found: $DUMP" "ملف قاعدة البيانات غير موجود"
    if [ -z "$FILESTORE" ]; then
        FILESTORE="$(find_filestore_for "$DUMP")"
    fi
    [ -n "$FILESTORE" ] || die "No filestore given/found (use --filestore DIR|FILE.tar.gz)" "لم يتم العثور على مجلد الملفات - حدده بـ --filestore"
    FILESTORE="$(readlink -f "$FILESTORE")"
    info "Dump      : $DUMP ($(du -h "$DUMP" | cut -f1))" "ملف قاعدة البيانات"
    info "Filestore : $FILESTORE ($(du -sh "$FILESTORE" | cut -f1))" "ملفات الموقع"
fi

# ------------------------------------------------------------- preflight ----
if [ "$SKIP_PF" = 0 ]; then
    step "Preflight" "الفحص المسبق"
    if ! "$KIT_DIR/preflight.sh" --phase trial ${DUMP:+--dump "$DUMP"}; then
        confirm "Preflight reported FAIL. Continue anyway?" "الفحص أظهر مشاكل. هل تريد المتابعة رغم ذلك؟" || die "Aborted." "تم الإلغاء."
    fi
fi

# -------------------------------------------------------------------- .env ----
step "Configuration (.env)" "ملف الإعدادات"
if [ ! -f "$ENV_FILE" ]; then
    install -m 600 "$ENV_EXAMPLE" "$ENV_FILE"
    info "Created $ENV_FILE from .env.example" "تم إنشاء ملف .env"
fi
chmod 600 "$ENV_FILE"
load_env
[ -n "$ARFA_DB_PASSWORD" ]  || set_env ARFA_DB_PASSWORD "$(gen_secret 24)"
[ -n "$ARFA_ADMIN_PASSWD" ] || set_env ARFA_ADMIN_PASSWD "$(gen_secret 24)"
[ "$NO_AUTH" = 1 ] && set_env ARFA_TRIAL_AUTH 0
if [ "$ARFA_TRIAL_AUTH" = "1" ] && [ -z "$ARFA_TRIAL_AUTH_PASSWORD" ]; then set_env ARFA_TRIAL_AUTH_PASSWORD "$(gen_readable 14)"; fi
if [ -z "$ARFA_PUBLIC_IP" ]; then
    ip="$(detect_public_ip)"; [ -n "$ip" ] || die "Cannot detect public IP - set ARFA_PUBLIC_IP in .env" "تعذّر اكتشاف عنوان IP - اكتبه في .env"
    set_env ARFA_PUBLIC_IP "$ip"
fi
load_env
[ -d "$ARFA_ADDONS_DIR/wasm_website" ] || die "wasm_website not found in $ARFA_ADDONS_DIR (set ARFA_ADDONS_DIR in .env)" "الموديول غير موجود في $ARFA_ADDONS_DIR"
mkdir -p "$ARFA_BACKUP_DIR" "$RUNTIME_DIR/logs"; chmod 700 "$RUNTIME_DIR" "$ARFA_BACKUP_DIR"
render_odoo_conf
ok "Secrets stored in $ENV_FILE (chmod 600)" "تم حفظ كلمات المرور في .env"

# -------------------------------------------------------------- database ----
step "Starting PostgreSQL (container, not published)" "تشغيل قاعدة البيانات"
dc pull -q db odoo || warn "image pull failed - using local images if present" "تعذّر تنزيل الصور - سيتم استخدام الموجود"
dc up -d db
wait_healthy db 120 || die "PostgreSQL did not become healthy (dc logs db)" "قاعدة البيانات لم تعمل - راجع السجلات"
ok "PostgreSQL healthy" "قاعدة البيانات تعمل"

NEED_RESTORE=0
if db_exists; then
    if [ -n "$DUMP" ]; then
        [ "$FORCE" = 1 ] || die "Database $ARFA_DB_NAME already exists. Re-run with --force to REPLACE it (a backup is taken first)." \
            "قاعدة البيانات $ARFA_DB_NAME موجودة مسبقاً. استخدم --force لاستبدالها (سيتم أخذ نسخة احتياطية أولاً)."
        confirm "REPLACE existing database $ARFA_DB_NAME and its files with the dump?" "هل تريد استبدال قاعدة البيانات الحالية وملفاتها؟" || die "Aborted." "تم الإلغاء."
        step "Safety backup before replacing" "نسخة احتياطية قبل الاستبدال"
        "$KIT_DIR/backup.sh" --tag pre-force-install
        dc stop odoo >/dev/null 2>&1 || true
        drop_db
        NEED_RESTORE=1
    else
        info "Database $ARFA_DB_NAME exists - no restore requested, keeping it." "قاعدة البيانات موجودة - لن تتم الاستعادة."
    fi
else
    [ -n "$DUMP" ] || die "Database $ARFA_DB_NAME does not exist: give --from DIR or --dump FILE --filestore PATH" \
        "قاعدة البيانات غير موجودة: حدد ملف النسخة عبر --from أو --dump و --filestore"
    NEED_RESTORE=1
fi

if [ "$NEED_RESTORE" = 1 ]; then
    step "Restoring database + filestore" "استعادة قاعدة البيانات والملفات"
    restore_db "$DUMP"
    restore_filestore "$FILESTORE"
    step "Upgrading modules ($ARFA_UPDATE_MODULES)" "تحديث الموديولات"
    odoo_update "$ARFA_UPDATE_MODULES" || die "Module upgrade failed - fix and re-run ./update.sh" "فشل تحديث الموديولات - راجع السجل ثم شغّل update.sh"
fi

# ---------------------------------------------------- base url / noindex ----
step "Website URL (trial) + hide from search engines" "رابط الموقع التجريبي وإخفاؤه عن محركات البحث"
MODE="$(state_get mode)"; [ -n "$MODE" ] || MODE=trial
apply_mode_params "$MODE"
state_set mode "$MODE"

# ------------------------------------------------------------------ odoo ----
step "Starting Odoo" "تشغيل أودو"
dc up -d --force-recreate odoo   # picks up the rendered odoo.conf and drops cached parameters
wait_healthy odoo 300 || { dc logs --tail 60 odoo >&2; die "Odoo is not healthy" "أودو لم يعمل بشكل سليم - راجع السجلات أعلاه"; }
code="$(curl -s -o /dev/null -w '%{http_code}' -H "X-Forwarded-Host: ${ARFA_PUBLIC_IP}:${ARFA_TRIAL_PORT}" "http://127.0.0.1:${ARFA_HTTP_PORT}/" || true)"
[ "$code" = "200" ] && ok "Odoo answers on 127.0.0.1:${ARFA_HTTP_PORT} (HTTP $code)" "أودو يعمل محلياً" \
                    || warn "Home page returned HTTP $code on 127.0.0.1:${ARFA_HTTP_PORT}" "الصفحة الرئيسية أعادت الرمز $code"

# ----------------------------------------------------------------- nginx ----
if [ "$NO_NGINX" = 0 ] && [ "$MODE" = "trial" ]; then
    "$KIT_DIR/enable_trial_nginx.sh" --no-params
fi

# --------------------------------------------------------------- summary ----
CRED="$RUNTIME_DIR/CREDENTIALS.txt"
{
    echo "ARFA production - generated $(date '+%F %T')"
    echo "Trial URL        : $(trial_url)"
    if [ "$ARFA_TRIAL_AUTH" = "1" ]; then
        echo "Trial username   : $ARFA_TRIAL_AUTH_USER"
        echo "Trial password   : $ARFA_TRIAL_AUTH_PASSWORD"
    fi
    echo "Odoo backend     : $(trial_url)/web/login  (same users as the restored database)"
    echo "Odoo master pwd  : $ARFA_ADMIN_PASSWD"
    echo "Database         : $ARFA_DB_NAME (container arfa_prod-db-1, not published)"
} > "$CRED"
chmod 600 "$CRED"

printf '\n%s======================= ARFA INSTALLED / تم التثبيت =======================%s\n' "$C_G" "$C_0"
cat "$CRED"
cat <<EOF

Send the client / أرسل للعميل:
  $(trial_url)$( [ "$ARFA_TRIAL_AUTH" = "1" ] && printf '\n  user: %s   password: %s' "$ARFA_TRIAL_AUTH_USER" "$ARFA_TRIAL_AUTH_PASSWORD")
Saved in $CRED (root only).
Next: ./status.sh   |   daily backups: ./backup.sh --install-cron
EOF
