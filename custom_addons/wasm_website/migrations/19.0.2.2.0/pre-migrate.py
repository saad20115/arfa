# -*- coding: utf-8 -*-
"""19.0.2.2.0 (before the XML data is loaded): log and remove implied groups of the wasm
groups that security/wasm_security.xml does not declare (production had "مدير عام" ->
Settings/Administration). The XML then sets the declared ones explicitly."""
import logging

_logger = logging.getLogger(__name__)

DECLARED = {
    'group_wasm_user': ('base', 'group_user'),
    'group_wasm_manager': ('wasm_website', 'group_wasm_user'),
}


def _group_id(cr, module, name):
    cr.execute("SELECT res_id FROM ir_model_data WHERE model = 'res.groups' AND module = %s AND name = %s",
               (module, name))
    row = cr.fetchone()
    return row and row[0]


def migrate(cr, version):
    for name, (imp_module, imp_name) in DECLARED.items():
        gid = _group_id(cr, 'wasm_website', name)
        allowed = _group_id(cr, imp_module, imp_name)
        if not gid:
            continue
        cr.execute("""
            SELECT r.hid, COALESCE(d.module || '.' || d.name, g.name->>'en_US')
              FROM res_groups_implied_rel r
              JOIN res_groups g ON g.id = r.hid
         LEFT JOIN ir_model_data d ON d.model = 'res.groups' AND d.res_id = r.hid
             WHERE r.gid = %s AND r.hid IS DISTINCT FROM %s
        """, (gid, allowed))
        rows = cr.fetchall()
        if rows:
            cr.execute("DELETE FROM res_groups_implied_rel WHERE gid = %s AND hid IN %s",
                       (gid, tuple(r[0] for r in rows)))
            _logger.warning('wasm_website security hardening: wasm_website.%s no longer implies %s',
                            name, ', '.join(r[1] for r in rows))
