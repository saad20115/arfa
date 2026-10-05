#!/usr/bin/env bash
# =============================================================================
# preflight.sh - read-only checks before installing ARFA on a shared VPS.
# فحص مسبق (قراءة فقط) قبل التثبيت على خادم يستضيف تطبيقات أخرى. لا يغيّر أي شيء.
# Usage: sudo ./preflight.sh [--phase trial|domain] [--dump FILE]
# Exit code: 0 = no FAIL, 1 = at least one FAIL.
# =============================================================================
set -euo pipefail
. "$(dirname "$0")/lib/common.sh"
. "$(dirname "$0")/lib/nginx.sh"

PHASE=trial; DUMP=""
while [ $# -gt 0 ]; do
    case "$1" in
        --phase) PHASE="$2"; shift 2;;
        --dump) DUMP="$2"; shift 2;;
        -h|--help) sed -n '2,8p' "$0"; exit 0;;
        *) die "Unknown option $1" "خيار غير معروف $1";;
    esac
done
load_env

NP=0; NW=0; NF=0
P() { NP=$((NP+1)); printf '%s[PASS]%s %s\n       %s\n' "$C_G" "$C_0" "$1" "${2:-}"; }
W() { NW=$((NW+1)); printf '%s[WARN]%s %s\n       %s\n' "$C_Y" "$C_0" "$1" "${2:-}"; }
F() { NF=$((NF+1)); printf '%s[FAIL]%s %s\n       %s\n' "$C_R" "$C_0" "$1" "${2:-}"; }
I() { printf '[INFO] %s\n       %s\n' "$1" "${2:-}"; }

DOCKER_OK=0
OUR_PORTS=""

step "System" "النظام"
[ "$(id -u)" -eq 0 ] && P "Running as root" "يعمل بصلاحية root" || W "Not root: some checks are incomplete" "ليس root - بعض الفحوص ناقصة، شغّل بـ sudo"
I "$(. /etc/os-release 2>/dev/null && echo "$PRETTY_NAME") / kernel $(uname -r)" "نظام التشغيل"
CPUS="$(nproc 2>/dev/null || echo 1)"
[ "$CPUS" -ge 2 ] && P "CPU cores: $CPUS (Odoo workers auto = $(compute_workers))" "عدد المعالجات: $CPUS" \
                 || W "CPU cores: $CPUS (shared with other apps)" "معالج واحد فقط - الأداء قد يتأثر"
MEM_AVAIL_MB="$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)"
MEM_TOTAL_MB="$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)"
if [ "$MEM_AVAIL_MB" -ge 2500 ]; then P "RAM available ${MEM_AVAIL_MB} MB / ${MEM_TOTAL_MB} MB" "الذاكرة المتاحة كافية"
elif [ "$MEM_AVAIL_MB" -ge 1200 ]; then W "RAM available only ${MEM_AVAIL_MB} MB - lower ARFA_WORKERS / ARFA_ODOO_MEM" "الذاكرة المتاحة قليلة - قلّل عدد العمال في .env"
else F "RAM available ${MEM_AVAIL_MB} MB (<1.2 GB)" "الذاكرة المتاحة غير كافية"; fi
SWAP_MB="$(awk '/SwapTotal/ {print int($2/1024)}' /proc/meminfo)"
[ "$SWAP_MB" -gt 0 ] || W "No swap configured" "لا توجد ذاكرة swap - يُنصح بإضافتها على خادم مشترك"

check_disk() { # check_disk <path> <label>
    local p="$1" free
    while [ ! -e "$p" ]; do p="$(dirname "$p")"; done
    free="$(df -Pm "$p" | awk 'NR==2 {print $4}')"
    if [ "$free" -ge 10240 ]; then P "Disk free on $p ($2): $((free/1024)) GB" "المساحة الحرة كافية"
    elif [ "$free" -ge 5120 ]; then W "Disk free on $p ($2): $((free/1024)) GB (<10 GB)" "المساحة الحرة قليلة"
    else F "Disk free on $p ($2): ${free} MB (<5 GB)" "المساحة الحرة غير كافية"; fi
    if [ -n "$DUMP" ] && [ -f "$DUMP" ]; then
        local need=$(( $(stat -c %s "$DUMP") / 1024 / 1024 * 6 ))
        [ "$free" -gt "$need" ] || F "Dump needs ~${need} MB free on $p" "حجم النسخة يحتاج مساحة أكبر"
    fi
}
check_disk "$ARFA_HOME" "ARFA_HOME / backups"

step "Docker" "Docker"
if have docker && docker info >/dev/null 2>&1; then
    DOCKER_OK=1
    P "Docker $(docker version -f '{{.Server.Version}}' 2>/dev/null)" "Docker يعمل"
    check_disk "$(docker info -f '{{.DockerRootDir}}' 2>/dev/null || echo /var/lib/docker)" "Docker data"
else
    F "Docker missing or daemon not reachable" "Docker غير مثبت أو لا يعمل"
fi
if docker compose version >/dev/null 2>&1; then
    P "Docker Compose $(docker compose version --short 2>/dev/null) (v2 plugin)" "Docker Compose v2 موجود"
else
    F "docker compose (v2 plugin) missing - docker-compose v1 is not supported" "إضافة docker compose v2 غير موجودة"
fi

step "Name collisions (containers / volumes / networks)" "تعارض الأسماء"
if [ "$DOCKER_OK" = 1 ]; then
    ours_label="com.docker.compose.project=$PROJECT"
    for kind in container volume network; do
        case "$kind" in
            container) names="$(docker ps -a --format '{{.Names}}')";;
            volume)    names="$(docker volume ls -q)";;
            network)   names="$(docker network ls --format '{{.Name}}')";;
        esac
        hits="$(printf '%s\n' "$names" | grep -Ei '^arfa' || true)"
        if [ -z "$hits" ]; then P "No $kind named arfa*" "لا يوجد $kind باسم arfa"; continue; fi
        while read -r n; do
            [ -z "$n" ] && continue
            proj="$(docker "$kind" inspect -f '{{ index .Labels "com.docker.compose.project" }}' "$n" 2>/dev/null || true)"
            if [ "$proj" = "$PROJECT" ]; then
                I "$kind $n belongs to this kit ($ours_label) - already installed" "هذا العنصر تابع لتثبيت عرفة سابق"
            elif grep -Eq '^(arfa_prod_db|arfa_prod_odoo|arfa_prod_net|arfa_prod[-_].*)$' <<< "$n"; then
                F "$kind '$n' exists but is NOT from this kit (project='${proj:-none}')" "يوجد عنصر بنفس الاسم لا يتبع هذا الكيت - تعارض"
            else
                W "$kind '$n' (project='${proj:-none}') - different name, no collision" "يوجد عنصر يبدأ بـ arfa لكن باسم مختلف - لا تعارض"
            fi
        done <<< "$hits"
    done
    wd="$(docker ps -a --filter "label=$ours_label" --format '{{.Label "com.docker.compose.project.working_dir"}}' 2>/dev/null | sort -u | head -1 || true)"
    if [ -n "$wd" ] && [ "$wd" != "$KIT_DIR" ]; then
        W "arfa_prod was installed from another folder: $wd" "تم التثبيت سابقاً من مجلد آخر: $wd - استخدم نفس المجلد"
    fi
fi

step "Ports" "المنافذ"
port_listeners() { ss -H -ltnp "sport = :$1" 2>/dev/null || true; }
port_bound_by_container() { # any container (even stopped) configured to publish this host port
    [ "$DOCKER_OK" = 1 ] || return 0
    local ids; ids="$(docker ps -aq)"; [ -n "$ids" ] || return 0
    # shellcheck disable=SC2086
    docker inspect -f '{{.Name}} {{range $p, $b := .HostConfig.PortBindings}}{{range $b}}{{.HostPort}} {{end}}{{end}}' $ids 2>/dev/null \
        | awk -v p="$1" '{for (i=2;i<=NF;i++) if ($i==p) print substr($1,2)}'
}
check_port() { # check_port <port> <label> <expected-owner-regex-if-ours>
    local p="$1" lab="$2" l c
    case "$p" in ''|*[!0-9]*) F "$lab: invalid port '$p'" "منفذ غير صالح"; return;; esac
    l="$(port_listeners "$p")"; c="$(port_bound_by_container "$p" | grep -v "^${PROJECT}-" || true)"
    if [ -n "$c" ]; then F "$lab port $p is reserved by another container: $c" "المنفذ $p محجوز لحاوية أخرى - غيّره في .env"; return; fi
    if [ -z "$l" ]; then P "$lab port $p is free" "المنفذ $p متاح"; return; fi
    if [ -n "$(port_bound_by_container "$p" | grep "^${PROJECT}-" || true)" ] || \
       { [ "$3" = "nginx" ] && grep -q nginx <<< "$l" && [ -f "$(state_get nginx_target)" ] && grep -q "listen .*$p" "$(state_get nginx_target)"; }; then
        P "$lab port $p is used by ARFA itself (already installed)" "المنفذ مستخدم من عرفة نفسها"
    else
        F "$lab port $p is already in use: $(printf '%s' "$l" | awk '{print $4, $6}' | head -2 | tr '\n' ' ')" "المنفذ $p مستخدم - اختر منفذاً آخر في .env"
    fi
}
if have ss; then
    check_port "$ARFA_HTTP_PORT" "Odoo HTTP (127.0.0.1)" docker
    check_port "$ARFA_CHAT_PORT" "Odoo websocket (127.0.0.1)" docker
    check_port "$ARFA_TRIAL_PORT" "Trial (public)" nginx
    [ "$ARFA_HTTP_PORT" != "$ARFA_CHAT_PORT" ] && [ "$ARFA_HTTP_PORT" != "$ARFA_TRIAL_PORT" ] && [ "$ARFA_CHAT_PORT" != "$ARFA_TRIAL_PORT" ] \
        || F "ARFA_HTTP_PORT / ARFA_CHAT_PORT / ARFA_TRIAL_PORT must differ" "يجب أن تكون المنافذ الثلاثة مختلفة"
    for p in 80 443; do
        l="$(port_listeners "$p")"
        I "Port $p: ${l:+$(printf '%s' "$l" | sed -n 's/.*users:((\"\([^\"]*\)\".*/\1/p' | head -1)}${l:-free}" "حالة المنفذ $p"
    done
else
    W "'ss' not found (iproute2) - port checks skipped" "أداة ss غير موجودة - لم يتم فحص المنافذ"
fi

step "Reverse proxy (nginx)" "خادم nginx"
MODE="$(nginx_mode)"
if host_nginx_present; then
    P "Host nginx detected ($(nginx -v 2>&1 | sed 's/.*: //')) -> drop-in mode" "تم اكتشاف nginx على الخادم - سيتم إضافة ملف مستقل فقط"
    if nginx -t >/dev/null 2>&1; then P "Existing nginx config is valid (nginx -t)" "إعدادات nginx الحالية سليمة"
    else F "Existing nginx config FAILS nginx -t - fix it before adding ARFA" "إعدادات nginx الحالية فيها خطأ - أصلحه أولاً"; fi
    tgt="$(host_nginx_target)"
    if [ -n "$tgt" ]; then
        P "Drop-in target: $tgt" "مكان ملف عرفة: $tgt"
        if [ -e "$tgt" ] && ! grep -q "$KIT_MARKER" "$tgt"; then F "$tgt exists and is not from this kit" "الملف موجود ولا يتبع الكيت"; fi
    else
        F "nginx.conf includes neither sites-enabled/ nor conf.d/*.conf" "لا يوجد include لمجلد sites-enabled أو conf.d"
    fi
    others="$(nginx_dump_others)"
    for name in arfa_prod_odoo arfa_prod_odoo_chat arfa_prod_forms arfa_prod_login arfa_prod_conn_upgrade arfa_prod_ssl; do
        grep -q "$name" <<< "$others" && F "nginx already defines '$name' outside our file" "الاسم $name معرّف مسبقاً في nginx"
    done
    if grep -Eq "^[^#]*server_name[^;]*[[:space:]](www\.)?${ARFA_DOMAIN//./\\.}[[:space:];]" <<< "$others"; then
        W "Another nginx vhost already uses server_name $ARFA_DOMAIN - remove it before phase 2" "يوجد موقع آخر في nginx يستخدم نفس النطاق"
    fi
    ipl="$(grep -Eo '^[^#]*listen[[:space:]]+[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+:(80|443)' <<< "$others" | awk '{print $NF}' | sort -u | tr '\n' ' ' || true)"
    [ -n "$ipl" ] && W "Other vhosts listen on explicit IPs ($ipl) - set ARFA_NGINX_LISTEN_IP to that IP for phase 2" \
                       "مواقع أخرى تستمع على عنوان IP محدد - اضبط ARFA_NGINX_LISTEN_IP"
    grep -Eq '^[^#]*listen[^;]*default_server' <<< "$others" && I "Another vhost owns default_server (fine - ARFA never uses it)" "يوجد default_server لتطبيق آخر - لا مشكلة"
else
    I "No host nginx -> the kit will run its own nginx container (docker-compose.nginx.yml)" "لا يوجد nginx على الخادم - سيتم استخدام حاوية nginx خاصة"
    if [ "$DOCKER_OK" = 1 ]; then
        px="$(docker ps --format '{{.Names}} {{.Image}} {{.Ports}}' | grep -Ei 'nginx|traefik|caddy|haproxy|apache|httpd' || true)"
        [ -n "$px" ] && W "Reverse-proxy containers found (phase 2 needs 80/443):" "توجد حاويات بروكسي أخرى:" && sed 's/^/       /' <<< "$px"
    fi
    if [ "$PHASE" = "domain" ]; then
        for p in 80 443; do
            [ -z "$(port_listeners "$p")" ] && P "Port $p free for the nginx container" "المنفذ $p متاح" \
                || F "Port $p is used by another service - phase 2 must be added to THAT proxy instead" "المنفذ $p مستخدم - يجب إضافة النطاق إلى البروكسي الحالي"
        done
    fi
fi
I "Effective nginx mode: $MODE" "وضع nginx المعتمد: $MODE"
have systemctl && { systemctl is-active --quiet apache2 2>/dev/null || systemctl is-active --quiet httpd 2>/dev/null; } && W "Apache is running on this host" "يوجد Apache يعمل على الخادم"

step "Other Odoo / PostgreSQL on this host (informative)" "تطبيقات أودو الأخرى (للمعلومية)"
if [ "$DOCKER_OK" = 1 ]; then
    od="$(docker ps -a --format '{{.Names}}|{{.Image}}|{{.Status}}|{{.Ports}}' | grep -Ei 'odoo|postgres' | grep -v "^${PROJECT}-" || true)"
    if [ -n "$od" ]; then printf '%s\n' "$od" | awk -F'|' '{printf "       - %-28s %-22s %-18s %s\n", $1, $2, substr($3,1,18), $4}'
    else I "No other Odoo/Postgres containers" "لا توجد حاويات أودو أخرى"; fi
fi
hp="$(pgrep -af 'odoo-bin|openerp-server|odoo/odoo' 2>/dev/null | grep -v pgrep | head -5 || true)"
[ -n "$hp" ] && I "Host Odoo processes: $(printf '%s' "$hp" | wc -l)" "عمليات أودو على الخادم مباشرة" && sed 's/^/       /' <<< "$hp"
have ss && { pg="$(ss -H -ltn 'sport = :5432' 2>/dev/null || true)"; [ -n "$pg" ] && I "Something listens on 5432 (host PostgreSQL) - ARFA does NOT use it" "يوجد PostgreSQL على الخادم - عرفة لا تستخدمه"; }
I "ARFA uses its own PostgreSQL container, DB '$ARFA_DB_NAME', dbfilter ^$ARFA_DB_NAME\$" "عرفة تستخدم قاعدة بيانات مستقلة تماماً"

step "Firewall" "الجدار الناري"
if have ufw && grep -q 'Status: active' <<< "$(ufw status 2>/dev/null || true)"; then
    if grep -Eq "^${ARFA_TRIAL_PORT}(/tcp)?[[:space:]]+ALLOW" <<< "$(ufw status)"; then P "ufw allows $ARFA_TRIAL_PORT/tcp" "الجدار الناري يسمح بالمنفذ"
    else W "ufw active: open the trial port with: ufw allow ${ARFA_TRIAL_PORT}/tcp" "افتح منفذ التجربة: ufw allow ${ARFA_TRIAL_PORT}/tcp"; fi
elif have firewall-cmd && firewall-cmd --state >/dev/null 2>&1; then
    W "firewalld active: firewall-cmd --permanent --add-port=${ARFA_TRIAL_PORT}/tcp && firewall-cmd --reload" "افتح منفذ التجربة في firewalld"
else
    I "No host firewall detected - also check the cloud provider firewall for port $ARFA_TRIAL_PORT" "تأكد أيضاً من جدار مزوّد الخدمة السحابية"
fi

step "DNS ($ARFA_DOMAIN)" "النطاق"
IP="${ARFA_PUBLIC_IP:-$(detect_public_ip)}"
I "Public IP: ${IP:-unknown}" "عنوان الخادم العام"
for h in "$ARFA_DOMAIN" "www.$ARFA_DOMAIN"; do
    r="$(getent ahostsv4 "$h" 2>/dev/null | awk '{print $1}' | sort -u | tr '\n' ' ' || true)"
    if [ -z "$r" ]; then
        [ "$PHASE" = "domain" ] && F "$h does not resolve" "النطاق $h لا يشير لأي عنوان" || I "$h does not resolve yet (fine for phase 1)" "النطاق غير مربوط بعد - طبيعي في المرحلة الأولى"
    elif grep -qw "$IP" <<< "$r"; then P "$h -> $r" "النطاق يشير إلى هذا الخادم"
    else
        [ "$PHASE" = "domain" ] && F "$h -> $r (expected $IP)" "النطاق يشير لعنوان آخر" || I "$h -> $r (not this server yet)" "النطاق يشير حالياً لخادم آخر"
    fi
done

step "Tools" "الأدوات"
for t in openssl curl ss flock tar gzip; do have "$t" && P "$t" "" || F "$t missing (apt-get install -y ${t/ss/iproute2})" "الأداة $t غير موجودة"; done
have htpasswd && P "htpasswd" "" || I "htpasswd missing - openssl will be used for the password file" "سيتم استخدام openssl بدلاً من htpasswd"
have git && P "git" "" || I "git missing (only needed for update.sh --git)" "git غير موجود"
if [ "$PHASE" = "domain" ]; then have certbot && P "certbot $(certbot --version 2>&1 | awk '{print $2}')" "" || W "certbot missing - enable_domain.sh will try apt/dnf install" "certbot غير مثبت"; fi
[ -d "$ARFA_ADDONS_DIR/wasm_website" ] && P "Addons found in $ARFA_ADDONS_DIR" "تم العثور على الموديولات" \
    || F "wasm_website not found in ARFA_ADDONS_DIR=$ARFA_ADDONS_DIR" "مجلد الموديولات غير موجود - عدّل ARFA_ADDONS_DIR"
[ -d "$ARFA_ADDONS_DIR/wasm_debrand" ] || W "wasm_debrand not found in $ARFA_ADDONS_DIR" "موديول wasm_debrand غير موجود"
[ -f /etc/cron.d/arfa_prod_backup ] && I "Backup cron installed: /etc/cron.d/arfa_prod_backup" "النسخ الاحتياطي المجدول مفعّل"

printf '\n==================== PREFLIGHT SUMMARY / ملخص الفحص ====================\n'
printf '  %sPASS %d%s   %sWARN %d%s   %sFAIL %d%s   (phase: %s, nginx mode: %s)\n' \
    "$C_G" "$NP" "$C_0" "$C_Y" "$NW" "$C_0" "$C_R" "$NF" "$C_0" "$PHASE" "$MODE"
if [ "$NF" -gt 0 ]; then
    printf '  RESULT: FAIL - fix the items above before installing.\n  النتيجة: فشل - أصلح البنود أعلاه قبل التثبيت.\n'; exit 1
fi
printf '  RESULT: PASS - safe to continue.\n  النتيجة: ناجح - يمكن المتابعة بأمان.\n'
