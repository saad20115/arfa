# -*- coding: utf-8 -*-
"""Runs at the end of EVERY update of wasm_website: create the website texts added by the new
version (existing texts edited by the admin are never changed), and keep the main menu
visible to visitors (see content_setup.wasm_fix_menu_visibility)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version:  # only on update (install is handled by the post_init_hook)
        env = api.Environment(cr, SUPERUSER_ID, {})
        env['wasm.text']._wasm_sync_defaults()
        from odoo.addons.wasm_website.content_setup import wasm_fix_menu_visibility
        wasm_fix_menu_visibility(env)
