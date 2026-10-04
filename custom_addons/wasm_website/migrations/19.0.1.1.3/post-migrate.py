# -*- coding: utf-8 -*-
"""19.0.1.1.3: drop compiled web asset bundles so Odoo rebuilds them.

The database was used from two locations with different filestores; some
compiled bundles (/web/assets/...) point to files that only exist in the other
location, which makes the CSS/JS return HTTP 500 (menu stays hidden, colors
missing). Odoo regenerates any bundle whose attachment is missing.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    bundles = env['ir.attachment'].sudo().search([('url', '=like', '/web/assets/%')])
    _logger.info('wasm_website: removing %s compiled asset bundles (they are rebuilt on demand)', len(bundles))
    bundles.unlink()
