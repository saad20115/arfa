# -*- coding: utf-8 -*-
"""19.0.2.1.0: meaningful reference numbers for website requests.

New requests get ARFA-RFQ-YYMM-NNNN (quote form) or ARFA-MSG-YYMM-NNNN (contact page);
the sequence keeps its running number and only supplies NNNN. Existing references are
left unchanged because they were already e-mailed to customers.
"""
from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    seq = env.ref('wasm_website.seq_wasm_quote_request', raise_if_not_found=False) \
        or env['ir.sequence'].search([('code', '=', 'wasm.quote.request')], limit=1)
    if seq:
        seq.sudo().write({'prefix': False, 'suffix': False, 'padding': 4})
