#!/usr/bin/env bash
# Odoo 19 supports Python 3.10 - 3.13. The system python3 on this machine is 3.14,
# so prefer the dedicated Python 3.12 virtualenv when it exists.
export PYTHONPATH="/home/saad/odoo 20/odoo19-community/usr/lib/python3/dist-packages:${PYTHONPATH}"
if [ -x "/home/saad/odoo19-venv/bin/python" ]; then
    PY="/home/saad/odoo19-venv/bin/python"
else
    PY="python3"
fi
"$PY" "/home/saad/odoo 20/odoo19-community/usr/bin/odoo" -c "/home/saad/arfa/odoo19-arfa2026.conf" "$@"
