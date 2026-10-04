# -*- coding: utf-8 -*-
"""19.0.1.1.2: website logo = stacked lockup (gold mark, company name underneath)."""
import base64
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    try:
        with file_open('wasm_website/static/src/img/arfa_logo_stacked.png', 'rb') as f:
            logo = base64.b64encode(f.read())
    except Exception:
        _logger.warning('wasm_website: stacked logo file not found, website logo left unchanged')
        return
    env['website'].search([]).write({'logo': logo})
