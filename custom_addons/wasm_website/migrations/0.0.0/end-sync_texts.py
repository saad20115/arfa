# -*- coding: utf-8 -*-
"""Runs at the end of EVERY update of wasm_website: create the website texts added by the new
version (existing texts edited by the admin are never changed)."""
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if version:  # only on update (install is handled by the post_init_hook)
        api.Environment(cr, SUPERUSER_ID, {})['wasm.text']._wasm_sync_defaults()
