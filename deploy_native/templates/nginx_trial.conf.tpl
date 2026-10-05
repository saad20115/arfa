# ARFA new website (Odoo 19) - TRIAL site, managed by deploy_native/10_install.sh - do not edit by hand
# Declares only: upstream arfa_new_odoo, arfa_new_chat; map $arfa_new_conn_upgrade; zones arfa_new_forms, arfa_new_login.
# Never default_server; listens only on its own port. Other sites (arfa-sa.conf, imdadconstgroup.conf) are untouched.
# Never uses default_server. Odoo listens on 127.0.0.1 only; this file is the only public entry.

upstream arfa_new_odoo {
    server 127.0.0.1:__HTTP_PORT__;
}
upstream arfa_new_chat {
    server 127.0.0.1:__CHAT_PORT__;
}
map $http_upgrade $arfa_new_conn_upgrade {
    default upgrade;
    ''      close;
}
limit_req_zone $binary_remote_addr zone=arfa_new_forms:10m rate=6r/m;
limit_req_zone $binary_remote_addr zone=arfa_new_login:10m rate=12r/m;

# ---------------- Phase 1: trial on http://SERVER_IP:__TRIAL_PORT__ (noindex, basic-auth) ----------------
server {
    listen __TRIAL_PORT__;
    server_name _;   # unique port -> no other vhost is involved; NOT default_server
    access_log /var/log/nginx/arfa_new.access.log;
    error_log /var/log/nginx/arfa_new.error.log warn;
    __AUTH__
    server_tokens off;
    proxy_hide_header X-Powered-By;
    proxy_hide_header X-Frame-Options;
    proxy_hide_header X-Content-Type-Options;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
    add_header X-Robots-Tag "noindex, nofollow, noarchive, nosnippet" always;  # trial: hidden from search engines

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

    proxy_set_header Host $http_host;
    proxy_set_header X-Forwarded-Host $http_host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header Authorization "";  # basic-auth credentials stay at nginx

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
        limit_req zone=arfa_new_forms burst=5 nodelay;
        client_max_body_size 50m;
        proxy_pass http://arfa_new_odoo;
    }
    location = /contactus/submit {
        limit_req zone=arfa_new_forms burst=5 nodelay;
        proxy_pass http://arfa_new_odoo;
    }
    location = /contact/submit {
        limit_req zone=arfa_new_forms burst=5 nodelay;
        proxy_pass http://arfa_new_odoo;
    }
    location = /web/login {
        limit_req zone=arfa_new_login burst=10 nodelay;
        proxy_pass http://arfa_new_odoo;
    }
    location = /web/session/authenticate {
        limit_req zone=arfa_new_login burst=10 nodelay;
        proxy_pass http://arfa_new_odoo;
    }
    location ^~ /web/reset_password {
        limit_req zone=arfa_new_login burst=5 nodelay;
        proxy_pass http://arfa_new_odoo;
    }

    # ---- live chat / bus (gevent) ----
    location /websocket {
        proxy_pass http://arfa_new_chat;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $arfa_new_conn_upgrade;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Authorization "";  # basic-auth credentials stay at nginx
    }

    # ---- backend + editor: large uploads (admin videos). Odoo itself caps a request at 128 MiB ----
    location ^~ /web/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_new_odoo;   # /web/assets/* keep Odoo's own long-cache headers
    }
    location ^~ /html_editor/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_new_odoo;
    }
    location ^~ /web_editor/ {
        client_max_body_size 200m;
        proxy_pass http://arfa_new_odoo;
    }

    # trial: block every crawler regardless of what Odoo serves
    location = /robots.txt {
        auth_basic off;
        default_type text/plain;
        return 200 "User-agent: *\nDisallow: /\n";
    }

    location / {
        proxy_pass http://arfa_new_odoo;   # /wasm/* image & video routes: Odoo cache headers pass through
    }
}
