#!/usr/bin/env bash
# =============================================================================
# update.sh - deploy new code of the custom addons: backup -> new code -> -u -> restart.
# تحديث الموقع: نسخة احتياطية ← الكود الجديد ← تحديث الموديولات ← إعادة التشغيل.
#
# Usage: sudo ./update.sh --git                       # git pull --ff-only in ARFA_HOME
#        sudo ./update.sh --addons-from /tmp/custom_addons   # copy a new custom_addons folder
#        sudo ./update.sh                             # code already in place: just upgrade
# Options: --modules wasm_website[,wasm_debrand]   (default: ARFA_UPDATE_MODULES)
#          --pull-image   also pull the (pinned) Odoo image
#          --no-backup    skip the pre-update backup (not recommended)
#          --render-config  re-render runtime/odoo.conf from .env / template
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"

GIT=0; FROM=""; MODS=""; PULL=0; BACKUP=1; RENDER=0
need_root; require_docker; require_env_file; load_env
while [ $# -gt 0 ]; do
    case "$1" in
        --git) GIT=1; shift;;
        --addons-from) FROM="$2"; shift 2;;
        --modules) MODS="$2"; shift 2;;
        --pull-image) PULL=1; shift;;
        --no-backup) BACKUP=0; shift;;
        --render-config) RENDER=1; shift;;
        -h|--help) sed -n '2,14p' "$0"; exit 0;;
        *) die "Unknown option: $1" "خيار غير معروف: $1";;
    esac
done
MODS="${MODS:-$ARFA_UPDATE_MODULES}"
[[ "$MODS" =~ ^[a-z0-9_,]+$ ]] || die "Invalid module list: $MODS" "قائمة الموديولات غير صحيحة"

LAST=""
if [ "$BACKUP" = 1 ]; then
    step "Backup before update" "نسخة احتياطية قبل التحديث"
    "$KIT_DIR/backup.sh" --tag pre-update
    LAST="$(cat "$RUNTIME_DIR/last_backup")"
fi

if [ "$GIT" = 1 ]; then
    step "git pull in $ARFA_HOME" "جلب الكود الجديد من git"
    have git || die "git not installed" "git غير مثبت"
    git -C "$ARFA_HOME" diff --quiet || die "Local changes in $ARFA_HOME - commit/stash them first (git -C $ARFA_HOME status)" "توجد تعديلات محلية غير محفوظة"
    old="$(git -C "$ARFA_HOME" rev-parse --short HEAD)"
    git -C "$ARFA_HOME" pull --ff-only
    new="$(git -C "$ARFA_HOME" rev-parse --short HEAD)"
    info "Code $old -> $new" "الكود: $old ← $new"
    git -C "$ARFA_HOME" log --oneline "$old..$new" | head -20 || true
fi

if [ -n "$FROM" ]; then
    step "Copying addons from $FROM" "نسخ الموديولات الجديدة"
    [ -d "$FROM/wasm_website" ] || die "$FROM does not contain wasm_website/" "المجلد لا يحتوي wasm_website"
    prev="$ARFA_HOME/.addons_prev_$(ts_now)"
    cp -a "$ARFA_ADDONS_DIR" "$prev"
    for m in "$FROM"/*/; do
        m="$(basename "$m")"; [ -f "$FROM/$m/__manifest__.py" ] || continue
        rm -rf "${ARFA_ADDONS_DIR:?}/$m.new"; cp -a "$FROM/$m" "$ARFA_ADDONS_DIR/$m.new"
        rm -rf "${ARFA_ADDONS_DIR:?}/$m"; mv "$ARFA_ADDONS_DIR/$m.new" "$ARFA_ADDONS_DIR/$m"
        info "updated addon $m" "تم تحديث $m"
    done
    find "$ARFA_ADDONS_DIR" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
    info "Previous addons kept in $prev" "النسخة السابقة من الموديولات محفوظة في $prev"
    # keep only the 3 most recent addon snapshots
    find "$ARFA_HOME" -maxdepth 1 -type d -name '.addons_prev_*' -printf '%T@ %p\n' | sort -rn | tail -n +4 | cut -d' ' -f2- | xargs -r rm -rf
fi

[ "$RENDER" = 1 ] && render_odoo_conf
if [ "$PULL" = 1 ]; then step "Pulling images" "تنزيل الصور"; dc pull odoo db; fi

step "Upgrading modules" "تحديث الموديولات"
if ! odoo_update "$MODS"; then
    dc up -d odoo >/dev/null 2>&1 || true
    err "UPDATE FAILED. The database transaction was rolled back, but the NEW code is in place." \
        "فشل التحديث. قاعدة البيانات لم تتغير لكن الكود الجديد موجود."
    printf 'Rollback / للتراجع:\n'
    [ "$GIT" = 1 ] && printf '  git -C %s reset --hard %s\n' "$ARFA_HOME" "$old"
    [ -n "$FROM" ] && printf '  rm -rf %s && cp -a %s %s\n' "$ARFA_ADDONS_DIR" "$prev" "$ARFA_ADDONS_DIR"
    [ -n "$LAST" ] && printf '  sudo %s/restore.sh --set %s   # only if data looks wrong\n' "$KIT_DIR" "$LAST"
    printf '  sudo docker compose -p %s restart odoo\n' "$PROJECT"
    exit 1
fi

step "Restarting Odoo" "إعادة تشغيل أودو"
dc up -d --force-recreate odoo
wait_healthy odoo 300 || { dc logs --tail 60 odoo >&2; die "Odoo not healthy after update" "أودو لم يعمل بعد التحديث"; }
code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$ARFA_HTTP_PORT/" || true)"
[ "$code" = "200" ] && ok "Home page HTTP 200" "الصفحة الرئيسية تعمل" || warn "Home page HTTP $code" "الصفحة الرئيسية أعادت $code"
ok "Update complete${LAST:+ (backup: $LAST)}" "اكتمل التحديث"
