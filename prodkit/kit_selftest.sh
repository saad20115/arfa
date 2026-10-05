#!/usr/bin/env bash
# =============================================================================
# kit_selftest.sh - validates THIS KIT itself (run it on the VPS first, or anywhere).
# فحص ذاتي لملفات الكيت نفسها: صحة السكربتات وملف compose وإعدادات nginx. لا يغيّر شيئاً.
#   - bash -n (and shellcheck if installed) on every script
#   - docker compose config (or python yaml fallback) + isolation rules
#   - renders every nginx layout and runs "nginx -t" on it in a throw-away prefix
#     (host nginx binary, else the nginx docker image, else skipped)
# Usage: ./kit_selftest.sh [--keep]   (--keep leaves the temp folder for inspection)
# =============================================================================
set -euo pipefail
KIT="$(cd "$(dirname "$0")" && pwd)"
KEEP=0; [ "${1:-}" = "--keep" ] && KEEP=1
T="$(mktemp -d /tmp/arfa_selftest.XXXXXX)"
[ "$KEEP" = 1 ] || trap 'rm -rf "$T"' EXIT
NP=0; NF=0; NS=0
P() { NP=$((NP+1)); printf '[PASS] %s\n' "$1"; }
F() { NF=$((NF+1)); printf '[FAIL] %s\n' "$1"; [ -n "${2:-}" ] && sed 's/^/       /' <<< "$2" | head -25; return 0; }
S() { NS=$((NS+1)); printf '[SKIP] %s\n' "$1"; }

# ------------------------------------------------------------------ bash ----
for f in "$KIT"/*.sh "$KIT"/lib/*.sh; do
    if out="$(bash -n "$f" 2>&1)"; then P "bash -n $(basename "$f")"; else F "bash -n $(basename "$f")" "$out"; fi
done
if command -v shellcheck >/dev/null 2>&1; then
    if out="$(cd "$KIT" && shellcheck -x -S error -e SC1091 ./*.sh lib/*.sh 2>&1)"; then P "shellcheck (errors)"; else F "shellcheck" "$out"; fi
else S "shellcheck not installed"; fi

# ------------------------------------------------------------- test env ----
ENVT="$T/.env"
sed -e 's/^ARFA_DB_PASSWORD=$/ARFA_DB_PASSWORD=selftestdbpass0123456789/' \
    -e 's/^ARFA_ADMIN_PASSWD=$/ARFA_ADMIN_PASSWD=selftestadmin0123456789/' \
    -e 's/^ARFA_TRIAL_AUTH_PASSWORD=$/ARFA_TRIAL_AUTH_PASSWORD=selftestpw/' \
    -e 's/^ARFA_PUBLIC_IP=$/ARFA_PUBLIC_IP=203.0.113.10/' \
    -e "s|^ARFA_ADDONS_DIR=.*|ARFA_ADDONS_DIR=$T/addons|" "$KIT/.env.example" > "$ENVT"
mkdir -p "$T/addons"

# --------------------------------------------------------------- compose ----
mkdir -p "$T/kit/runtime"; cp "$KIT"/docker-compose*.yml "$T/kit/"; : > "$T/kit/runtime/db_password"; : > "$T/kit/runtime/odoo.conf"
CJSON="$T/compose.json"
if docker compose version >/dev/null 2>&1; then
    if out="$(docker compose -p arfa_prod --env-file "$ENVT" -f "$T/kit/docker-compose.prod.yml" config --format json 2>&1)"; then
        printf '%s' "$out" > "$CJSON"; P "docker compose config (prod)"
    else F "docker compose config (prod)" "$out"; fi
    if out="$(COMPOSE_PROFILES=trial,domain docker compose -p arfa_prod --env-file "$ENVT" -f "$T/kit/docker-compose.prod.yml" -f "$T/kit/docker-compose.nginx.yml" config -q 2>&1)"; then
        P "docker compose config (prod + nginx container, both profiles)"
    else F "docker compose config (nginx override)" "$out"; fi
else
    S "docker compose not available - using python yaml"
fi
if [ ! -s "$CJSON" ] && command -v python3 >/dev/null; then
    python3 - "$T/kit/docker-compose.prod.yml" "$CJSON" <<'PY' && P "YAML parses (python)" || F "YAML parse (python)"
import sys, yaml, json, re, os
raw = open(sys.argv[1]).read()
def sub(m):
    name, default = m.group(1), m.group(3) or ''
    return os.environ.get(name, default)
raw = re.sub(r'\$\{([A-Z_]+)(:-([^}]*))?\}', sub, raw).replace('$$', '$')
d = yaml.safe_load(raw); d.setdefault('name', 'arfa_prod')
json.dump(d, open(sys.argv[2], 'w'))
PY
fi
if [ -s "$CJSON" ]; then
    if out="$(python3 - "$CJSON" <<'PY' 2>&1
import json, sys
d = json.load(open(sys.argv[1])); errs = []
if d.get('name') != 'arfa_prod': errs.append('project name is not arfa_prod')
s = d['services']
if s['db'].get('ports'): errs.append('db publishes ports')
for p in s['odoo'].get('ports', []):
    ip = p.get('host_ip') if isinstance(p, dict) else str(p).split(':')[0]
    if ip != '127.0.0.1': errs.append('odoo port not bound to 127.0.0.1: %s' % p)
for n, svc in s.items():
    if svc.get('container_name') and not svc['container_name'].startswith('arfa_'): errs.append('container_name %s' % n)
    if svc.get('restart') != 'unless-stopped': errs.append('%s restart policy' % n)
    if 'healthcheck' not in svc: errs.append('%s has no healthcheck' % n)
    if not (svc.get('mem_limit') or svc.get('deploy', {}).get('resources')): errs.append('%s has no mem_limit' % n)
    if (svc.get('logging') or {}).get('driver') != 'json-file': errs.append('%s logging' % n)
for v in d.get('volumes', {}).values():
    if not v.get('name', '').startswith('arfa_prod_'): errs.append('volume name %s' % v)
for v in d.get('networks', {}).values():
    if not v.get('name', '').startswith('arfa_prod_'): errs.append('network name %s' % v)
print('\n'.join(errs)); sys.exit(1 if errs else 0)
PY
)"; then P "compose isolation rules (no db port, odoo on 127.0.0.1, named volumes/network, limits, healthchecks, log rotation)"
    else F "compose isolation rules" "$out"; fi
fi

# ------------------------------------------------------------- odoo.conf ----
if out="$(ARFA_ENV_FILE="$ENVT" bash -c '
    set -euo pipefail; . "'"$KIT"'/lib/common.sh"; RUNTIME_DIR="'"$T"'/rt"; load_env; render_odoo_conf >/dev/null
    for k in "proxy_mode = True" "list_db = False" "dbfilter = ^arfa_prod\$" "max_cron_threads = 1" "db_maxconn = 32" "data_dir = /var/lib/odoo" "with_demo = False"; do
        grep -qxF "$k" "$RUNTIME_DIR/odoo.conf" || { echo "missing: $k"; exit 1; }
    done' 2>&1)"; then P "odoo.conf renders with required production keys"; else F "odoo.conf render" "$out"; fi

# ----------------------------------------------------------------- nginx ----
NGX=""
if command -v nginx >/dev/null 2>&1; then NGX=host
elif docker info >/dev/null 2>&1; then NGX=docker; fi
openssl req -x509 -newkey rsa:2048 -nodes -days 2 -subj '/CN=arfa-sa.com' -keyout "$T/key.pem" -out "$T/cert.pem" >/dev/null 2>&1
nginx_ge_1251() { local v; v="$(nginx -v 2>&1 | sed -n 's|.*nginx/\([0-9.]*\).*|\1|p')"; [ "$(printf '1.25.1\n%s\n' "$v" | sort -V | head -1)" = "1.25.1" ]; }
mime="include /etc/nginx/mime.types;"; [ -f /etc/nginx/mime.types ] || mime=""
for target in host container; do
  for layout in trial acme domain; do
    for keep in 0 1; do
      [ "$layout" = trial ] && [ "$keep" = 1 ] && continue
      tag="$layout/$target/keep=$keep"; f="$T/ngx_${layout}_${target}_${keep}.conf"
      if ! out="$(ARFA_ENV_FILE="$ENVT" ARFA_HSTS=1 bash -c '
            set -euo pipefail; . "'"$KIT"'/lib/common.sh"; . "'"$KIT"'/lib/nginx.sh"; load_env
            render_nginx "$1" "$2" "$3"' _ "$layout" "$target" "$keep" 2>&1 > "$f")"; then F "render $tag" "$out"; continue; fi
      # isolation lint
      lint=""
      grep -Eq '^[^#]*listen[^;]*default_server' "$f" && lint+="uses default_server; "
      for n in $(grep -Eo '^(upstream|map [^ ]+) +\$?[A-Za-z0-9_]+' "$f" | awk '{print $NF}' | tr -d '$'); do
          [[ "$n" == arfa_prod_* ]] || lint+="name $n not prefixed; "
      done
      for z in $(grep -Eo 'zone=[a-z0-9_]+' "$f" | cut -d= -f2 | sort -u) $(grep -Eo 'shared:[a-z0-9_]+' "$f" | cut -d: -f2 | sort -u); do
          [[ "$z" == arfa_prod_* ]] || lint+="zone $z not prefixed; "
      done
      if [ "$layout" = trial ] || [ "$keep" = 1 ]; then grep -q 'X-Robots-Tag "noindex' "$f" || lint+="trial without noindex; "; fi
      if [ "$layout" = domain ]; then
          awk '/^server \{/{b=""} {b=b"\n"$0} /^\}/{ if (b ~ /listen 443/ && b ~ /X-Robots-Tag/) bad=1 } END{exit bad}' "$f" || lint+="noindex on https; "
      fi
      [ -z "$lint" ] && P "render + isolation lint $tag" || F "isolation lint $tag" "$lint"
      if [ -z "$NGX" ]; then continue; fi
      d="$T/ngx_${layout}_${target}_${keep}"; mkdir -p "$d/logs"
      # the container image (1.27) supports "http2 on;" - an older host binary used for the test does not
      h2sed='s|^$||'; [ "$NGX" = host ] && [ "$target" = container ] && ! nginx_ge_1251 && h2sed='s|^ *http2 on;||'
      sed -e "s|/etc/letsencrypt/live/[^/]*/fullchain.pem|$( [ "$NGX" = docker ] && echo /t/cert.pem || echo "$T/cert.pem")|" \
          -e "s|/etc/letsencrypt/live/[^/]*/privkey.pem|$( [ "$NGX" = docker ] && echo /t/key.pem || echo "$T/key.pem")|" \
          -e 's|server odoo:|server 127.0.0.1:|' -e "$h2sed" \
          -e "s|/var/log/nginx/|$( [ "$NGX" = docker ] && echo /tmp/ || echo "$d/logs/")|" "$f" > "$d/site.conf"
      if [ "$NGX" = host ]; then
          cat > "$d/nginx.conf" <<EOF
pid $d/nginx.pid;
error_log $d/logs/error.log;
events { worker_connections 64; }
http { $mime access_log off; client_body_temp_path $d/cb; proxy_temp_path $d/px; fastcgi_temp_path $d/fc; uwsgi_temp_path $d/uw; scgi_temp_path $d/sc;
  include $d/site.conf; }
EOF
          out="$(nginx -t -q -p "$d" -c "$d/nginx.conf" -e "$d/logs/error.log" 2>&1)" && P "nginx -t $tag (host nginx $(nginx -v 2>&1 | sed 's|.*/||'))" || F "nginx -t $tag" "$out"
      else
          cp "$T/cert.pem" "$T/key.pem" "$d/"
          printf 'events {}\nhttp { include /etc/nginx/mime.types; include /t/site.conf; }\n' > "$d/nginx.conf"
          out="$(docker run --rm -v "$d:/t:ro" nginx:1.27-alpine nginx -t -q -c /t/nginx.conf 2>&1)" && P "nginx -t $tag (docker nginx:1.27)" || F "nginx -t $tag" "$out"
      fi
    done
  done
done
[ -z "$NGX" ] && S "nginx -t skipped (no nginx binary and no docker daemon)"

printf '\n=========== KIT SELFTEST: PASS %d  FAIL %d  SKIP %d ===========\n' "$NP" "$NF" "$NS"
[ "$KEEP" = 1 ] && echo "temp files kept in $T"
[ "$NF" -eq 0 ]
