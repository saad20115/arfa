# -*- coding: utf-8 -*-
"""Editable website texts.

Every fixed text of the website (section headings, paragraphs, button labels,
form labels, footer...) is a ``wasm.text`` record identified by a ``key``.
Templates read it with ``site_config.tx('home.why.title')``.

Default values live in ``models/texts/*.py``. Missing records are created on
install/upgrade (and from the backend button), so new keys appear automatically
and texts edited by the admin are never overwritten.
"""
from markupsafe import Markup, escape

from odoo import api, fields, models, tools

from .texts import PAGES, TEXT_DEFAULTS


class WasmText(models.Model):
    _name = 'wasm.text'
    _description = 'نصوص الموقع - Website Texts'
    _order = 'page, sequence, id'
    _rec_name = 'label'

    key = fields.Char(string='المفتاح التقني', required=True, index=True, readonly=True)
    page = fields.Selection(PAGES, string='الصفحة', required=True, default='layout', index=True)
    label = fields.Char(string='مكان الظهور', required=True)
    sequence = fields.Integer(string='الترتيب', default=10)
    multiline = fields.Boolean(string='نص متعدد الأسطر')
    value_en = fields.Text(string='النص (English)')
    value_ar = fields.Text(string='النص (عربي)')
    default_en = fields.Text(string='النص الأصلي (English)', compute='_compute_defaults')
    is_modified = fields.Boolean(string='معدّل', compute='_compute_defaults')

    _key_unique = models.Constraint('UNIQUE(key)', 'Each website text key must be unique.')

    @api.depends('key', 'value_en', 'value_ar')
    def _compute_defaults(self):
        for rec in self:
            spec = TEXT_DEFAULTS.get(rec.key)
            rec.default_en = spec['en'] if spec else False
            rec.is_modified = bool(spec) and ((rec.value_en or '') != (spec['en'] or '')
                                              or (rec.value_ar or '') != (spec['ar'] or ''))

    # ------------------------------------------------------------------
    # cache: one query per language per page render
    # ------------------------------------------------------------------
    @api.model
    @tools.ormcache()
    def _wasm_all_values(self):
        self.env.cr.execute('SELECT key, value_en, value_ar FROM wasm_text')
        return {key: (en or '', ar or '') for key, en, ar in self.env.cr.fetchall()}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        self.env.registry.clear_cache()
        return records

    def write(self, vals):
        res = super().write(vals)
        self.env.registry.clear_cache()
        return res

    def unlink(self):
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @api.model
    def get_text(self, key, lang=None):
        """Text for the visitor language, falling back to the other language then to the default."""
        lang = lang or self.env.lang or 'en_US'
        is_en = lang.startswith('en')
        en, ar = self._wasm_all_values().get(key, ('', ''))
        spec = TEXT_DEFAULTS.get(key) or {}
        if is_en:
            return en or ar or spec.get('en') or spec.get('ar') or ''
        return ar or en or spec.get('ar') or spec.get('en') or ''

    @api.model
    def get_text_br(self, key, lang=None):
        """Escaped text with line breaks kept (for paragraphs)."""
        text = self.get_text(key, lang)
        return Markup('<br/>').join(escape(line) for line in text.split('\n'))

    # ------------------------------------------------------------------
    # defaults
    # ------------------------------------------------------------------
    @api.model
    def _wasm_sync_defaults(self):
        """Create missing keys; refresh page/label/order of existing ones (values are kept)."""
        existing = {rec.key: rec for rec in self.sudo().with_context(active_test=False).search([])}
        to_create = []
        for seq, (key, spec) in enumerate(TEXT_DEFAULTS.items()):
            meta = {'page': spec['page'], 'label': spec['label'], 'sequence': seq, 'multiline': spec['multiline']}
            rec = existing.get(key)
            if rec:
                if any(rec[f] != v for f, v in meta.items()):
                    rec.write(meta)
            else:
                to_create.append(dict(meta, key=key, value_en=spec['en'], value_ar=spec['ar']))
        if to_create:
            self.sudo().create(to_create)
        return len(to_create)

    def action_reset_default(self):
        for rec in self:
            spec = TEXT_DEFAULTS.get(rec.key)
            if spec:
                rec.write({'value_en': spec['en'], 'value_ar': spec['ar']})

    @api.model
    def action_sync_defaults(self):
        count = self._wasm_sync_defaults()
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': 'نصوص الموقع', 'type': 'success', 'sticky': False,
                       'message': 'تمت إضافة %s نص جديد.' % count if count else 'كل النصوص موجودة.'},
        }
