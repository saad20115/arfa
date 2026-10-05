# -*- coding: utf-8 -*-
"""19.0.2.0.0: the whole website becomes editable from the backend.

Moves the old fixed homepage cards (pillars, stats, why-choose-us, service cards)
from wasm.site.config into wasm.content.item / wasm.service, turns the hardcoded
service pages into wasm.service records with their galleries, and creates the
editable texts. Existing content is never overwritten.
"""
from odoo import api, SUPERUSER_ID

from odoo.addons.wasm_website.content_setup import wasm_install_content


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    wasm_install_content(env)
