#!/usr/bin/env bash
# 00_check.sh - READ-ONLY checks before installing ARFA next to the existing Odoo apps.
# فحص للقراءة فقط قبل التثبيت: لا يغيّر أي شيء في السيرفر.
. "$(dirname "$0")/lib.sh"
set +e
PASS=0; FAIL=0; WARNS=0
p() { ok "$1" "$2"; PASS=$((PASS+1)); }
f() { printf '%s[FAIL]%s %s | %s\n' "$c_err" "$c_off" "$1" "$2"; FAIL=$((FAIL+1)); }
w() { warn "$1" "$2"; WARNS=$((WARNS+1)); }

step "System" "النظام"
[ "$(id -u)" = 0 ] && p "running as root" "يعمل كـ root" || f "not root" "شغّل كـ root"
. /etc/os-release 2>/dev/null; echo "OS: ${PRETTY_NAME:-?} | CPU: $(nproc) | RAM free: $(free -g | awk '/Mem/{print $7}') GB"
avail=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
[ "${avail:-0}" -ge 10 ] && p "disk free ${avail} GB" "مساحة كافية" || f "disk free ${avail} GB < 10" "المساحة غير كافية"
memfree=$(free -m | awk '/Mem/{print $7}')
[ "${memfree:-0}" -ge 2500 ] && p "RAM available ${memfree} MB" "ذاكرة كافية" || w "RAM available ${memfree} MB (lower WORKERS)" "قلّل WORKERS"

step "Names already used?" "هل الأسماء مستخدمة؟"
id "$ARFA_USER" >/dev/null 2>&1 && w "Linux user '$ARFA_USER' exists (ok on re-run)" "المستخدم موجود" || p "Linux user '$ARFA_USER' free" "اسم المستخدم متاح"
systemctl list-unit-files "$SERVICE.service" 2>/dev/null | grep -q "$SERVICE.service" && w "service $SERVICE exists (ok on re-run)" "الخدمة موجودة" || p "service name $SERVICE free" "اسم الخدمة متاح"
for d in "$ARFA_RUNTIME" "$CONF_DIR" "$DATA_DIR"; do [ -e "$d" ] && w "$d exists (ok on re-run)" "المجلد موجود" || p "$d free" "المجلد متاح"; done
[ -e "$NGINX_SITE" ] && w "$NGINX_SITE exists (ok on re-run)" "ملف nginx موجود" || p "nginx file arfa_new.conf free" "ملف nginx متاح"

step "Ports" "المنافذ"
for port in "$HTTP_PORT" "$CHAT_PORT" "$TRIAL_PORT"; do
  if port_busy "$port"; then
    who=$(ss -ltnpH "( sport = :$port )" | sed -E 's/.*users:\(\("([^"]+)".*/\1/' | head -1)
    if [ "$port" = "$TRIAL_PORT" ] && [ "$who" = nginx ] && grep -qs "listen $TRIAL_PORT" "$NGINX_SITE"; then w "port $port used by our own nginx site (re-run)" "المنفذ مستخدم من موقعنا"
    elif [ "$who" = python3 ] && systemctl is-active -q "$SERVICE" 2>/dev/null; then w "port $port used by $SERVICE (re-run)" "المنفذ مستخدم من خدمتنا"
    else f "port $port is busy ($who) - change it in config.env" "المنفذ مشغول - غيّره في config.env"; fi
  else p "port $port free" "المنفذ متاح"; fi
done
echo "Other apps (left untouched): $(ss -ltnpH | grep -E ':(8069|8070|8072|8073) ' | awk '{print $4}' | tr '\n' ' ')"

step "PostgreSQL" "قاعدة البيانات"
if as_pg psql -XAtc "select version()" >/tmp/arfa_pgv 2>&1; then
  p "PostgreSQL reachable: $(cut -d' ' -f1-2 /tmp/arfa_pgv)" "متصل"
  echo "Existing databases: $(as_pg psql -XAtc "select string_agg(datname, ', ') from pg_database where not datistemplate")"
  db_exists && w "database $DB_NAME already exists (install will refuse without --force)" "القاعدة موجودة" || p "database name $DB_NAME free" "اسم القاعدة متاح"
  role_exists && w "role $ARFA_USER exists (ok on re-run)" "الدور موجود" || p "role $ARFA_USER free" "اسم الدور متاح"
  grep -qsE '^\s*local\s+all\s+all\s+peer' /etc/postgresql/*/main/pg_hba.conf && p "local peer authentication enabled" "المصادقة المحلية متاحة" || w "pg_hba: 'local all all peer' not found - check authentication" "راجع pg_hba"
else f "cannot reach PostgreSQL as user postgres" "تعذر الاتصال بقاعدة البيانات"; fi

step "nginx" "nginx"
if command -v nginx >/dev/null; then
  nginx -t >/tmp/arfa_nginx_t 2>&1 && p "nginx config valid (before our change)" "إعدادات nginx سليمة" || f "nginx -t fails BEFORE our change - fix that first" "إعدادات nginx فيها خطأ حالياً"
  grep -rqsE "listen\s+$TRIAL_PORT\b" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ --exclude=arfa_new.conf && f "another nginx site listens on $TRIAL_PORT" "موقع آخر يستخدم المنفذ"
  grep -rqsE "upstream\s+arfa_new_" /etc/nginx/sites-enabled/ /etc/nginx/conf.d/ --exclude=arfa_new.conf && f "upstream name arfa_new_* already used" "اسم upstream مستخدم"
  echo "Existing sites (left untouched): $(ls /etc/nginx/sites-enabled/ | tr '\n' ' ')"
else f "nginx not installed" "nginx غير مثبت"; fi

step "Tools & network" "الأدوات والشبكة"
for t in git python3 openssl curl pg_restore; do command -v $t >/dev/null && p "$t found" "موجود" || f "$t missing" "غير موجود"; done
pyv=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])'); python3 -c 'import sys;sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)' && p "python $pyv supported by Odoo 19" "إصدار بايثون مناسب" || f "python $pyv not supported (3.10-3.13)" "إصدار بايثون غير مناسب"
python3 -c 'import venv, ensurepip' 2>/dev/null && p "python3-venv available" "متاح" || w "python3-venv missing (install will apt-get it)" "سيتم تثبيته"
curl -s -m 10 -o /dev/null https://github.com && p "github.com reachable" "الوصول لـ GitHub" || f "github.com not reachable" "لا يوجد وصول لـ GitHub"
curl -s -m 10 -o /dev/null https://pypi.org/simple/ && p "pypi.org reachable" "الوصول لـ PyPI" || f "pypi.org not reachable" "لا يوجد وصول لـ PyPI"
[ -d "$ARFA_REPO/custom_addons/wasm_website" ] && p "addons found in $ARFA_REPO/custom_addons" "الموديولات موجودة" || f "$ARFA_REPO/custom_addons/wasm_website not found (git clone the repo first)" "انسخ المستودع أولاً"
v=$(grep -oE "'version': *'[^']+'" "$ARFA_REPO/custom_addons/wasm_website/__manifest__.py" 2>/dev/null | cut -d"'" -f4); echo "wasm_website version in repo: ${v:-?}"

step "Summary" "الخلاصة"
printf 'PASS %s | WARN %s | FAIL %s\n' "$PASS" "$WARNS" "$FAIL"
[ "$FAIL" = 0 ] && { ok "ready to install" "جاهز للتثبيت"; exit 0; } || { printf '%s[NOT READY]%s fix the FAIL lines first | أصلح البنود الفاشلة أولاً\n' "$c_err" "$c_off"; exit 1; }
