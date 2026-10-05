# -*- coding: utf-8 -*-
"""Repeated content blocks of the website (cards, stats, team members, links...).

One model for every list on the site; ``section`` says where an item appears.
Templates loop over ``site_config.items('why')`` etc.
"""
import base64
import logging

from odoo import api, fields, models
from odoo.tools.misc import file_open

from .texts import ITEM_SEEDS
from .wasm_mixins import ITEM_PX, wasm_check_urls

_logger = logging.getLogger(__name__)

SECTIONS = [
    ('pillar', 'الرئيسية: كروت الواجهة'),
    ('stat', 'الرئيسية: الإحصائيات'),
    ('why', 'الرئيسية: لماذا عرفة'),
    ('team', 'الرئيسية: فريق العمل'),
    ('expertise', 'من نحن: مجالات الخبرة'),
    ('division', 'شركتنا: الأقسام والشركات'),
    ('department', 'تواصل معنا: الأقسام'),
    ('footer_link', 'الفوتر: روابط سريعة'),
    ('footer_dept', 'الفوتر: روابط الأقسام'),
    ('bot_chip', 'المساعد الذكي: أسئلة سريعة'),
    ('bot_reply', 'المساعد الذكي: الردود'),
]


class WasmContentItem(models.Model):
    _name = 'wasm.content.item'
    _description = 'عناصر محتوى الموقع - Website Content Items'
    _order = 'section, sequence, id'
    _rec_name = 'title_en'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'image': ITEM_PX}

    section = fields.Selection(SECTIONS, string='القسم', required=True, index=True)
    sequence = fields.Integer(string='الترتيب', default=10)
    active = fields.Boolean(string='ظاهر في الموقع', default=True)

    title_en = fields.Char(string='العنوان (English)')
    title_ar = fields.Char(string='العنوان (عربي)')
    subtitle_en = fields.Char(string='عنوان فرعي / وظيفة (English)')
    subtitle_ar = fields.Char(string='عنوان فرعي / وظيفة (عربي)')
    desc_en = fields.Text(string='الوصف (English)')
    desc_ar = fields.Text(string='الوصف (عربي)')
    badge_en = fields.Char(string='شارة (English)')
    badge_ar = fields.Char(string='شارة (عربي)')
    value = fields.Char(string='القيمة / الرقم', help='للإحصائيات مثل 150+')
    icon = fields.Char(string='الأيقونة', help='اسم أيقونة FontAwesome مثل fa-building')
    link_url = fields.Char(string='الرابط', help='مثال: /services أو https://...')
    link_label_en = fields.Char(string='نص الرابط (English)')
    link_label_ar = fields.Char(string='نص الرابط (عربي)')
    image = fields.Image(string='الصورة', max_width=1600, max_height=1600)
    image_url = fields.Char(string='رابط صورة خارجي', help='يُستخدم فقط إذا لم تُرفع صورة')

    @api.constrains('link_url', 'image_url')
    def _check_wasm_urls(self):
        wasm_check_urls(self, url_fields=('image_url',), link_fields=('link_url',))

    # ------------------------------------------------------------------
    def t(self, base):
        """Bilingual value of <base>_en / <base>_ar for the visitor language (with fallback)."""
        self.ensure_one()
        is_en = (self.env.lang or 'en_US').startswith('en')
        first, second = ('_en', '_ar') if is_en else ('_ar', '_en')
        return self[base + first] or self[base + second] or ''

    def img_url(self):
        self.ensure_one()
        if self.image:
            unique = str(int(self.write_date.timestamp())) if self.write_date else '0'
            return '/wasm/item/%s/image?unique=%s' % (self.id, unique)
        return self.image_url or ''

    def desc_lines(self):
        """Description split into non-empty lines (for bullet lists)."""
        self.ensure_one()
        return [line.strip() for line in (self.t('desc') or '').splitlines() if line.strip()]

    # ------------------------------------------------------------------
    @api.model
    def _wasm_seed(self, sections=None, module_path='wasm_website'):
        """Create the default items of every section that has no item at all (archived count too)."""
        Item = self.sudo().with_context(active_test=False)
        created = 0
        by_section = {}
        for seed in ITEM_SEEDS:
            by_section.setdefault(seed['section'], []).append(seed)
        for section, seeds in by_section.items():
            if sections and section not in sections:
                continue
            if Item.search_count([('section', '=', section)]):
                continue
            vals_list = []
            for seq, seed in enumerate(seeds, start=1):
                vals = {k: v for k, v in seed.items() if k in self._fields and k != 'image'}
                vals.setdefault('sequence', seq * 10)
                image_file = seed.get('image_file')
                if image_file:
                    data = self._wasm_read_module_file(image_file, module_path)
                    if data:
                        vals['image'] = data
                vals_list.append(vals)
            Item.create(vals_list)
            created += len(vals_list)
        return created

    @api.model
    def _wasm_read_module_file(self, rel_path, module_path='wasm_website'):
        """base64 content of a file shipped in the module (static/src/...), or False."""
        rel_path = rel_path.lstrip('/')
        if rel_path.startswith(module_path + '/'):
            rel_path = rel_path[len(module_path) + 1:]
        try:
            with file_open('%s/%s' % (module_path, rel_path), 'rb') as fh:
                return base64.b64encode(fh.read())
        except (OSError, ValueError):
            _logger.warning('wasm_website: default file not found: %s', rel_path)
            return False
