#!/usr/bin/env bash
# shellcheck shell=bash
# =============================================================================
# ARFA production kit - nginx config renderer + installer (sourced, never run).
# Generates ONE self-contained file "arfa_prod.conf" (http context) that only
# declares names prefixed arfa_prod_ and never uses default_server.
# =============================================================================

NGINX_FILE_NAME="arfa_prod.conf"
NGINX_HTPASSWD="/etc/nginx/arfa_prod.htpasswd"     # host-nginx mode
NGINX_HTPASSWD_CT="/etc/nginx/conf.d/arfa_prod.htpasswd"   # container mode (runtime/nginx is mounted on conf.d)
NGINX_RUNTIME_DIR="$RUNTIME_DIR/nginx"

nginx_version_ge() { # nginx_version_ge 1.25.1 (host binary)
    local v; v="$(nginx -v 2>&1 | sed -n 's|.*nginx/\([0-9.]*\).*|\1|p')"
    [ -n "$v" ] && [ "$(printf '%s\n%s\n' "$1" "$v" | sort -V | head -1)" = "$1" ]
}

# configuration of every OTHER app on the host nginx (our own file excluded)
nginx_dump_others() {
    have nginx || return 0
    nginx -T 2>/dev/null | awk -v f="$NGINX_FILE_NAME" '
        /^# configuration file / { skip = (index($0, f) > 0) }
        !skip { print }' || true
}

# host_nginx_target -> prints the path where our drop-in must live
host_nginx_target() {
    local dump; dump="$(nginx_dump_others)"
    [ -n "$dump" ] || dump="$(cat /etc/nginx/nginx.conf 2>/dev/null || true)"   # nginx -T unavailable (broken config)
    if [ -d /etc/nginx/sites-enabled ] && grep -Eq '^[^#]*include[[:space:]]+/etc/nginx/sites-enabled/' <<< "$dump"; then
        printf '/etc/nginx/sites-available/%s' "$NGINX_FILE_NAME"
    elif grep -Eq '^[^#]*include[[:space:]]+/etc/nginx/conf\.d/\*\.conf' <<< "$dump"; then
        printf '/etc/nginx/conf.d/%s' "$NGINX_FILE_NAME"
    else
        printf ''
    fi
}

_hdr_block() { # _hdr_block <indent> <host-var> : standard proxy headers
    local i="$1" hv="$2"
    printf '%sproxy_set_header Host %s;\n' "$i" "$hv"
    printf '%sproxy_set_header X-Forwarded-Host %s;\n' "$i" "$hv"
    printf '%sproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n' "$i"
    printf '%sproxy_set_header X-Forwarded-Proto $scheme;\n' "$i"
    printf '%sproxy_set_header X-Real-IP $remote_addr;\n' "$i"
    if [ "$_R_STRIP_AUTH" = "1" ]; then
        printf '%sproxy_set_header Authorization "";  # basic-auth credentials stay at nginx\n' "$i"
    fi
}

_security_headers() { # _security_headers <noindex 0|1> <hsts 0|1>
    cat <<'EOF'
    server_tokens off;
    proxy_hide_header X-Powered-By;
    proxy_hide_header X-Frame-Options;
    proxy_hide_header X-Content-Type-Options;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
EOF
    if [ "$1" = "1" ]; then
        printf '    add_header X-Robots-Tag "noindex, nofollow, noarchive, nosnippet" always;  # trial: hidden from search engines\n'
    fi
    if [ "$2" = "1" ]; then
        printf '    add_header Strict-Transport-Security "max-age=31536000" always;  # HSTS (enabled with --hsts)\n'
    fi
}

# _odoo_body <host-var> <noindex> : everything that proxies to Odoo (shared by trial + domain)
# NOTE: no location below uses add_header, so the server-level security headers always apply.
_odoo_body() {
    local hv="$1" noindex="$2"
    cat <<'EOF'
    client_max_body_size 50m;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;
    proxy_read_timeout 720s;
    proxy_buffers 16 64k;
    proxy_buffer_size 128k;
    proxy_redirect off;
    limit_req_status 429;

    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript text/markdown application/javascript application/json application/xml application/rss+xml image/svg+xml;

EOF
    _hdr_block "    " "$hv"
    cat <<'EOF'

    location = /arfa-nginx-health {
        auth_basic off;
        access_log off;
        allow 127.0.0.1;
        allow ::1;
        deny all;
        default_type text/plain;
        return 200 "ok\n";
    }

    # ---- never public: DB manager, server info, external RPC APIs ----
    location ^~ /web/database { return 404; }
    location ^~ /website/info { return 404; }
    location ^~ /xmlrpc       { return 403; }
    location ^~ /jsonrpc      { return 403; }
    location ^~ /json/        { return 403; }   # Odoo 19 JSON-2 API
    location = /doc           { return 404; }
    location ^~ /doc/         { return 404; }

    # ---- rate-limited public forms (per client IP) ----
    location = /quote/submit {
        limit_req zone=arfa_prod_forms burst=5 nodelay;
        client_max_body_size 50m;
        proxy_pass http://arfa_prod_odoo;
    }
    location = /contactus/submit {
        limit_req zone=arfa_prod_forms burst=5 nodelay;
        proxy_pass http://arfa_prod_odoo;
    }
    location = /contact/submit {
        limit_req zone=arfa_prod_forms burst=5 nodelay;
        proxy_pass http://arfa_prod_odoo;
    }
    location = /web/login {
        limit_req zone=arfa_prod_login burst=10 nodelay;
        proxy_pass http://arfa_prod_odoo;
    }
    location = /web/session/authenticate {
        limit_req zone=arfa_prod_login burst=10 nodelay;
        proxy_pass http://arfa_prod_odoo;
    }
    location ^~ /web/reset_password {
        limit_req zone=arfa_prod_login burst=5 nodelay;
        proxy_pass http://arfa_prod_odoo;
    }

    # ---- live chat / bus (gevent) ----
    location /websocket {
        proxy_pass http://arfa_prod_odoo_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $arfa_prod_conn_upgrade;
EOF
    _hdr_block "        " "$hv"
    cat <<'EOF'
    }

    # ---- backend + editor: large uploads (admin videos). Odoo itself caps a request at 128 MiB ----
    location ^~ /web/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_prod_odoo;   # /web/assets/* keep Odoo's own long-cache headers
    }
    location ^~ /html_editor/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_prod_odoo;
    }
    location ^~ /web_editor/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_prod_odoo;
    }
EOF
    if [ "$noindex" = "1" ]; then
        cat <<'EOF'

    # trial: block every crawler regardless of what Odoo serves
    location = /robots.txt {
        auth_basic off;
        default_type text/plain;
        return 200 "User-agent: *\nDisallow: /\n";
    }
EOF
    fi
    cat <<'EOF'

    location / {
        proxy_pass http://arfa_prod_odoo;   # /wasm/* image & video routes: Odoo cache headers pass through
    }
EOF
}

_acme_location() {
    cat <<EOF
    location ^~ /.well-known/acme-challenge/ {
        auth_basic off;
        root $ARFA_ACME_WEBROOT;
        default_type text/plain;
        try_files \$uri =404;
    }
EOF
}

_listen() { # _listen <port> [ssl] [v6 0|1]
    local p="$1" ssl="${2:-}" v6="${3:-0}" sfx=""
    [ "$ssl" = "ssl" ] && sfx=" ssl"
    printf '    listen %s%s%s;\n' "$_R_LISTEN_IP" "$p" "$sfx"
    [ "$v6" = "1" ] && [ -z "$_R_LISTEN_IP" ] && printf '    listen [::]:%s%s;\n' "$p" "$sfx"
    return 0
}

_logs() {
    if [ "$_R_TARGET" = "container" ]; then
        printf '    access_log /dev/stdout;\n    error_log /dev/stderr warn;\n'
    else
        printf '    access_log /var/log/nginx/arfa_prod.access.log;\n    error_log /var/log/nginx/arfa_prod.error.log warn;\n'
    fi
}

_trial_server() {
    _R_STRIP_AUTH="$_R_AUTH"   # credentials of the trial password never reach Odoo
    printf '\n# ---------------- Phase 1: trial on http://SERVER_IP:%s (noindex%s) ----------------\n' \
        "$ARFA_TRIAL_PORT" "$( [ "$_R_AUTH" = 1 ] && printf ', basic-auth')"
    printf 'server {\n'
    _listen "$ARFA_TRIAL_PORT" "" "$_R_V6_TRIAL"
    printf '    server_name _;   # unique port -> no other vhost is involved; NOT default_server\n'
    _logs
    if [ "$_R_AUTH" = "1" ]; then
        printf '    auth_basic "ARFA preview";\n    auth_basic_user_file %s;\n' "$_R_HTPASSWD"
    fi
    _security_headers 1 0
    printf '\n'
    _odoo_body '$http_host' 1     # keep :PORT in Host so Odoo redirects stay on the trial port
    printf '}\n'
}

_ssl_common() {
    local cert="/etc/letsencrypt/live/$ARFA_DOMAIN"
    printf '    ssl_certificate %s/fullchain.pem;\n    ssl_certificate_key %s/privkey.pem;\n' "$cert" "$cert"
    printf '    ssl_protocols TLSv1.2 TLSv1.3;\n'
    printf '    ssl_session_cache shared:arfa_prod_ssl:10m;\n    ssl_session_timeout 1d;\n    ssl_session_tickets off;\n'
    [ "$_R_HTTP2" = "1" ] && printf '    http2 on;\n'
    return 0
}

_domain_servers() { # _domain_servers acme|final
    _R_STRIP_AUTH=0
    local apex="$ARFA_DOMAIN" www="www.$ARFA_DOMAIN" canon other
    canon="$(canonical_host)"; if [ "$canon" = "$apex" ]; then other="$www"; else other="$apex"; fi
    printf '\n# ---------------- Phase 2: %s / %s (canonical: %s) ----------------\n' "$apex" "$www" "$canon"
    printf 'server {\n'
    _listen 80 "" "$_R_V6_WEB"
    printf '    server_name %s %s;\n' "$apex" "$www"
    _logs
    printf '    server_tokens off;\n'
    _acme_location
    cat <<'EOF'
    location = /arfa-nginx-health {
        access_log off;
        allow 127.0.0.1;
        allow ::1;
        deny all;
        default_type text/plain;
        return 200 "ok\n";
    }
EOF
    if [ "$1" = "acme" ]; then
        printf '    location / { return 404; }   # temporary: certificate being issued\n}\n'
        return 0
    fi
    printf '    location / { return 301 https://%s$request_uri; }\n}\n' "$canon"

    printf '\nserver {\n'
    _listen 443 ssl "$_R_V6_WEB"
    printf '    server_name %s;\n' "$other"
    _logs
    _ssl_common
    _security_headers 0 "$ARFA_HSTS"
    printf '    location / { return 301 https://%s$request_uri; }\n}\n' "$canon"

    printf '\nserver {\n'
    _listen 443 ssl "$_R_V6_WEB"
    printf '    server_name %s;\n' "$canon"
    _logs
    _ssl_common
    _security_headers 0 "$ARFA_HSTS"
    printf '\n'
    _odoo_body '$host' 0
    printf '}\n'
}

# render_nginx <layout: trial|acme|domain> <target: host|container> <keep_trial 0|1>
render_nginx() {
    local layout="$1" up_http up_chat others=""
    _R_TARGET="$2"
    local keep_trial="${3:-0}"
    _R_AUTH=0; [ "$ARFA_TRIAL_AUTH" = "1" ] && [ -n "$ARFA_TRIAL_AUTH_PASSWORD" ] && _R_AUTH=1
    _R_STRIP_AUTH="$_R_AUTH"
    _R_LISTEN_IP=""; _R_V6_TRIAL=0; _R_V6_WEB=0; _R_HTTP2=0; _R_HTPASSWD="$NGINX_HTPASSWD"
    if [ "$_R_TARGET" = "container" ]; then
        _R_HTPASSWD="$NGINX_HTPASSWD_CT"
        up_http="odoo:8069"; up_chat="odoo:8072"
        [ "$ARFA_HTTP2" != "0" ] && _R_HTTP2=1          # nginx:1.27 image supports "http2 on"
    else
        up_http="127.0.0.1:$ARFA_HTTP_PORT"; up_chat="127.0.0.1:$ARFA_CHAT_PORT"
        [ -n "$ARFA_NGINX_LISTEN_IP" ] && _R_LISTEN_IP="$ARFA_NGINX_LISTEN_IP:"
        others="$(nginx_dump_others)"
        if [ "$ARFA_IPV6" = "1" ] || { [ "$ARFA_IPV6" = "auto" ] && [ -s /proc/net/if_inet6 ]; }; then
            _R_V6_TRIAL=1
            # only join IPv6 :80/:443 if other vhosts already listen there (else we'd become their v6 default)
            if [ "$ARFA_IPV6" = "1" ] || grep -Eq '^[^#]*listen[[:space:]]+\[::\]:80([^0-9]|$)' <<< "$others"; then _R_V6_WEB=1; fi
        fi
        if [ "$ARFA_HTTP2" = "1" ] || { [ "$ARFA_HTTP2" = "auto" ] && nginx_version_ge 1.25.1; }; then _R_HTTP2=1; fi
    fi
    # the trial block is part of trial/acme layouts, and of domain when explicitly kept
    local with_trial=0
    case "$layout" in trial) with_trial=1;; acme|domain) [ "$keep_trial" = "1" ] && with_trial=1;; esac

    cat <<EOF
$KIT_MARKER - DO NOT EDIT BY HAND (re-run enable_trial_nginx.sh / enable_domain.sh)
# ARFA website (Odoo 19) - layout: $layout - target: $_R_TARGET - generated $(date -u '+%Y-%m-%d %H:%M UTC')
# Declares only: upstream arfa_prod_odoo, arfa_prod_odoo_chat; map \$arfa_prod_conn_upgrade;
#                limit_req zones arfa_prod_forms, arfa_prod_login; ssl cache arfa_prod_ssl.
# Never uses default_server. Odoo listens on 127.0.0.1 only; this file is the only public entry.

upstream arfa_prod_odoo {
    server $up_http;
}
upstream arfa_prod_odoo_chat {
    server $up_chat;
}
map \$http_upgrade \$arfa_prod_conn_upgrade {
    default upgrade;
    ''      close;
}
limit_req_zone \$binary_remote_addr zone=arfa_prod_forms:10m rate=6r/m;
limit_req_zone \$binary_remote_addr zone=arfa_prod_login:10m rate=12r/m;
EOF
    [ "$with_trial" = "1" ] && _trial_server
    case "$layout" in
        acme)   _domain_servers acme ;;
        domain) _domain_servers final ;;
    esac
    return 0
}

write_htpasswd() { # write_htpasswd <file>  (bcrypt via htpasswd, else apr1 via openssl)
    local f="$1" hash
    mkdir -p "$(dirname "$f")"
    if [ "$ARFA_TRIAL_AUTH" != "1" ] || [ -z "$ARFA_TRIAL_AUTH_PASSWORD" ]; then : > "$f"; return 0; fi
    if have htpasswd; then
        htpasswd -bcB "$f" "$ARFA_TRIAL_AUTH_USER" "$ARFA_TRIAL_AUTH_PASSWORD" >/dev/null 2>&1
    else
        hash="$(openssl passwd -apr1 "$ARFA_TRIAL_AUTH_PASSWORD")"
        printf '%s:%s\n' "$ARFA_TRIAL_AUTH_USER" "$hash" > "$f"
    fi
}

nginx_worker_group() {
    local u; u="$(sed -n 's/^[[:space:]]*user[[:space:]]\+\([^ ;]*\).*/\1/p' /etc/nginx/nginx.conf 2>/dev/null | head -1)"
    [ -n "$u" ] && id -gn "$u" 2>/dev/null || true
}

# install_nginx_conf <layout> [keep_trial] : render, install, test, reload (rollback on failure)
install_nginx_conf() {
    local layout="$1" keep="${2:-0}" mode tmp target prev grp
    mode="$(nginx_mode)"
    mkdir -p "$NGINX_RUNTIME_DIR"
    tmp="$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME.new"
    render_nginx "$layout" "$mode" "$keep" > "$tmp"

    if [ "$mode" = "host" ]; then
        have nginx || die "nginx not found on host" "nginx غير موجود على الخادم"
        target="$(host_nginx_target)"
        [ -n "$target" ] || die "Cannot find sites-enabled/ or conf.d/*.conf include in nginx.conf" \
            "لم يتم العثور على مجلد sites-enabled أو conf.d في إعدادات nginx - أضف الملف يدوياً."
        if [ -e "$target" ] && ! grep -q "$KIT_MARKER" "$target"; then
            die "$target exists and was NOT created by this kit - refusing to overwrite." "الملف $target موجود ولم ينشئه هذا الكيت - لن يتم استبداله."
        fi
        nginx -t >/dev/null 2>&1 || die "Existing nginx config is already broken (nginx -t fails) - fix it first; nothing changed." \
            "إعدادات nginx الحالية فيها خطأ مسبق - أصلحها أولاً. لم يتم تغيير أي شيء."
        if [ -f "$NGINX_HTPASSWD" ] || [ "$_R_AUTH" = "1" ]; then
            write_htpasswd "$NGINX_HTPASSWD"
            grp="$(nginx_worker_group)"
            if [ -n "$grp" ]; then chown "root:$grp" "$NGINX_HTPASSWD"; chmod 640 "$NGINX_HTPASSWD"; else chmod 644 "$NGINX_HTPASSWD"; fi
        fi
        prev=""
        [ -f "$target" ] && { prev="$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME.prev"; cp -a "$target" "$prev"; }
        install -m 644 "$tmp" "$target"
        if [[ "$target" == /etc/nginx/sites-available/* ]]; then
            ln -sfn "$target" "/etc/nginx/sites-enabled/$NGINX_FILE_NAME"
        fi
        if ! nginx -t 2>"$NGINX_RUNTIME_DIR/nginx-t.log"; then
            cat "$NGINX_RUNTIME_DIR/nginx-t.log" >&2
            if [ -n "$prev" ]; then cp -a "$prev" "$target"; else rm -f "$target" "/etc/nginx/sites-enabled/$NGINX_FILE_NAME"; fi
            die "nginx -t failed - previous state restored, nginx NOT reloaded." "فشل اختبار nginx - تمت إعادة الوضع السابق ولم تتم إعادة تحميل nginx."
        fi
        if have systemctl && systemctl is-active --quiet nginx; then systemctl reload nginx; else nginx -s reload; fi
        cp -a "$tmp" "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME"
        state_set nginx_target "$target"
        ok "nginx drop-in installed: $target (nginx reloaded, other sites untouched)" "تم تركيب ملف nginx الخاص بعرفة وإعادة التحميل دون المساس بالمواقع الأخرى"
    else
        write_htpasswd "$NGINX_RUNTIME_DIR/arfa_prod.htpasswd"; chmod 644 "$NGINX_RUNTIME_DIR/arfa_prod.htpasswd"
        # runtime/nginx/ is bind-mounted (as a directory) on /etc/nginx/conf.d in the container
        [ -f "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME" ] && cp -a "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME" "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME.prev"
        mv "$tmp" "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME"
        chmod 644 "$NGINX_RUNTIME_DIR/$NGINX_FILE_NAME"
        ok "nginx container config written: $NGINX_RUNTIME_DIR/$NGINX_FILE_NAME" "تم إنشاء إعدادات حاوية nginx"
    fi
}

# start/switch the nginx container (container mode only): start_nginx_container trial|domain
start_nginx_container() {
    local want="$1" other cid
    if [ "$want" = "trial" ]; then other="domain"; else other="trial"; fi
    COMPOSE_PROFILES="$other" docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f "$COMPOSE_FILE" -f "$NGINX_COMPOSE_FILE" \
        rm -sf "nginx_$other" >/dev/null 2>&1 || true
    state_set mode "$want"
    if ! dc run --rm --no-deps -T "nginx_$want" nginx -t; then
        die "nginx container config test failed (see above)" "فشل اختبار إعدادات حاوية nginx (راجع الرسائل أعلاه)"
    fi
    dc up -d "nginx_$want"
    cid="$(dc ps -q "nginx_$want" | head -1)"
    [ -n "$cid" ] && docker exec "$cid" nginx -s reload >/dev/null 2>&1 || true
    ok "nginx container nginx_$want running" "حاوية nginx تعمل"
}

nginx_reload_cmd() { # command certbot runs after renewals
    if [ "$(nginx_mode)" = "host" ]; then
        printf 'systemctl reload nginx || nginx -s reload'
    else
        printf 'docker compose -p %s --env-file %s -f %s -f %s --profile domain exec -T nginx_domain nginx -s reload' \
            "$PROJECT" "$ENV_FILE" "$COMPOSE_FILE" "$NGINX_COMPOSE_FILE"
    fi
}
