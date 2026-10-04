# -*- coding: utf-8 -*-
"""19.0.1.2.0: new project detail page.

The project page template was fully redesigned (facts card, collapsible
sections, filterable gallery, previous/next). A website-specific copy saved
from the Website Builder would hide the new design, so it is removed here
(a backup of its HTML is kept as an attachment).
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    views = env['ir.ui.view'].with_context(active_test=False).search([
        ('key', '=', 'wasm_website.project_detail_page_template'),
        ('website_id', '!=', False),
    ])
    for view in views:
        env['ir.attachment'].create({
            'name': 'backup_%s_website%s_view%s.xml' % (view.key, view.website_id.id, view.id),
            'type': 'binary',
            'raw': (view.arch_db or '').encode('utf-8'),
            'mimetype': 'application/xml',
        })
        _logger.info('wasm_website: removing website copy of %s (view %s)', view.key, view.id)
        view.unlink()
