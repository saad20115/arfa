# -*- coding: utf-8 -*-
"""Upgrade to 19.0.1.1.0 (run automatically by: -u wasm_website).

1. Removes website-specific copies of this module's templates that were
   corrupted by the old slider / typewriter scripts (cloned slides and runtime
   flags saved by the Website Builder). Those frozen copies hide every change
   made in the module files, so updates to the homepage never showed up.
   A backup of each removed copy is kept as an attachment.
2. Fills the Arabic config fields that still contain the old English defaults.
3. Installs the new horizontal logo (gold mark + company name) on the website.
"""
import base64
import logging

from odoo import SUPERUSER_ID, api
from odoo.tools.misc import file_open

_logger = logging.getLogger(__name__)

CORRUPTION_MARKERS = ('wasm-slider-clone', 'data-slider-initialized', 'data-typewriter-initialized')
OLD_HERO_DEFAULT = "Building Saudi Arabia's Infrastructure Vision"
NEW_HERO_EN = 'Pioneering Engineering & Construction Excellence'


def _clean_corrupted_cow_views(env):
    View = env['ir.ui.view'].with_context(active_test=False)
    views = View.search([('key', '=like', 'wasm_website.%'), ('website_id', '!=', False)])
    for view in views:
        arch = view.arch_db or ''
        if not any(marker in arch for marker in CORRUPTION_MARKERS):
            continue
        env['ir.attachment'].create({
            'name': 'backup_%s_website%s_view%s.xml' % (view.key, view.website_id.id, view.id),
            'type': 'binary',
            'raw': arch.encode('utf-8'),
            'mimetype': 'application/xml',
            'description': 'Backup of a corrupted website-specific template copy removed by wasm_website 19.0.1.1.0',
        })
        _logger.info('wasm_website: removing corrupted website copy of %s (view %s)', view.key, view.id)
        view.unlink()


def _fill_arabic_texts(env):
    from odoo.addons.wasm_website.models.wasm_site_config import AR_DEFAULTS

    for config in env['wasm.site.config'].search([]):
        vals = {}
        for ar_field, ar_text in AR_DEFAULTS.items():
            if ar_field not in config._fields:
                continue
            en_field = ar_field[:-3] + '_en'
            current = config[ar_field]
            if not current or (en_field in config._fields and current == config[en_field]):
                vals[ar_field] = ar_text
        if config.hero_title_en in (False, '', OLD_HERO_DEFAULT):
            vals['hero_title_en'] = NEW_HERO_EN
        if vals:
            config.write(vals)


def _install_logo(env):
    try:
        with file_open('wasm_website/static/src/img/arfa_logo_horizontal.png', 'rb') as f:
            logo = base64.b64encode(f.read())
    except Exception:
        _logger.warning('wasm_website: new logo file not found, website logo left unchanged')
        return
    env['website'].search([]).write({'logo': logo})


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _clean_corrupted_cow_views(env)
    _fill_arabic_texts(env)
    _install_logo(env)
