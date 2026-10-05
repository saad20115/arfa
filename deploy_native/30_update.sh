#!/usr/bin/env bash
# 30_update.sh - apply a new version of the website code: git pull, backup, module update, restart.
# تحديث الموقع لنسخة جديدة من GitHub: سحب الكود، نسخة احتياطية، تحديث الموديول، إعادة التشغيل.
. "$(dirname "$0")/lib.sh"
need_root
step "1/4 Get new code" "جلب الكود الجديد"
git -C "$ARFA_REPO" pull --ff-only
chmod -R a+rX "$ARFA_REPO/custom_addons"
step "2/4 Backup" "نسخة احتياطية"
"$KIT_DIR/20_backup.sh"
step "3/4 Update module" "تحديث الموديول"
systemctl stop "$SERVICE"
odoo_run -d "$DB_NAME" -u wasm_website,wasm_debrand --stop-after-init --no-http --logfile=/dev/stdout --log-level=warn 2>&1 | grep -vE "must have title|View error context|^\{|^ '|Missing not-null|create the logfile" | tail -20 || true
step "4/4 Start" "التشغيل"
systemctl start "$SERVICE"
for i in $(seq 1 40); do curl -s -o /dev/null -m 3 "http://127.0.0.1:$HTTP_PORT/web/login" && break; sleep 2; done
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 "http://127.0.0.1:$HTTP_PORT/")
v=$(psql_db -Atc "select latest_version from ir_module_module where name='wasm_website'")
[ "$code" = 200 ] && ok "updated to $v, site OK" "تم التحديث" || die "site answers HTTP $code - restore with: ./20_backup.sh backups in $BACKUP_DIR" "الموقع لا يستجيب"
