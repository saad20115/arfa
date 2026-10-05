# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models

from .wasm_mixins import BANNER_PX, CARD_PX

# Services that already had their own root URL (kept for SEO and the website menu).
LEGACY_SLUGS = (
    'planning-construction', 'electromechanical-systems', 'smart-building-systems', 'modern-building-systems',
    'fire-protection-prevention-systems', 'medical-gas-systems', 'alternative-energy-solutions',
    'infrastructure-development',
)


class WasmService(models.Model):
    _name = 'wasm.service'
    _description = 'خدمات شركة عرفة الهندسية'
    _order = 'sequence, id'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'image': CARD_PX, 'banner_image': BANNER_PX}

    name = fields.Char(string='اسم الخدمة (يظهر في الكروت)', required=True, translate=True)
    sequence = fields.Integer(string='الترتيب', default=10)
    icon = fields.Char(string='أيقونة الخدمة', default='fa-building-o', help='اسم الفئة من FontAwesome مثل fa-wrench, fa-bolt, fa-building-o')
    image = fields.Image(string='صورة الكارت', max_width=1600, max_height=1600)
    short_description = fields.Text(string='وصف مختصر للخدمة (صفحة الخدمات)', translate=True)
    card_description = fields.Text(string='وصف كارت الصفحة الرئيسية', translate=True,
                                   help='النص تحت اسم الخدمة في سلايدر الصفحة الرئيسية. إذا تُرك فارغاً يُستخدم الوصف المختصر')
    detailed_description = fields.Html(string='شرح مفصل (اختياري، يظهر في صفحة الخدمة)', translate=True)

    category = fields.Selection([
        ('civil', 'الأعمال الإنشائية وبناء العظم'),
        ('mep', 'الأعمال الكهربائية والميكانيكية (MEP)'),
        ('hvac', 'أعمال التكييف والتبريد المركزية'),
        ('finishing', 'أعمال التشطيبات الفاخرة والديكور'),
        ('renovation', 'أعمال الترميم والتأهيل الهيكلي'),
        ('general', 'عام'),
    ], string='تصنيف الخدمة', default='general', required=True)

    active = fields.Boolean(string='نشط على الموقع', default=True)
    show_on_home = fields.Boolean(string='تظهر في سلايدر الصفحة الرئيسية', default=True)

    # --- service page ---
    slug = fields.Char(string='رابط الصفحة', help='مثال: medical-gas-systems (حروف إنجليزية صغيرة وشرطات فقط)')
    page_title = fields.Char(string='عنوان صفحة الخدمة', translate=True, help='إذا تُرك فارغاً يُستخدم اسم الخدمة')
    badge = fields.Char(string='الشارة أعلى الصفحة', translate=True)
    intro = fields.Text(string='المقدمة (تحت العنوان)', translate=True)
    features = fields.Text(string='المميزات (سطر لكل ميزة)', translate=True)
    banner_image = fields.Image(string='صورة البانر في صفحة الخدمة', max_width=1920, max_height=1200)
    media_ids = fields.One2many('wasm.gallery.image', 'service_id', string='معرض صور وفيديوهات الخدمة')
    website_url = fields.Char(string='رابط الخدمة في الموقع', compute='_compute_website_url')

    _slug_unique = models.Constraint('UNIQUE(slug)', 'رابط الخدمة مستخدم لخدمة أخرى.')

    @api.depends('slug')
    def _compute_website_url(self):
        for rec in self:
            if not rec.slug:
                rec.website_url = '/services'
            elif rec.slug in LEGACY_SLUGS:
                rec.website_url = '/%s' % rec.slug
            else:
                rec.website_url = '/services/%s' % rec.slug

    @staticmethod
    def _wasm_slugify(text):
        return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')[:80] or False

    def _wasm_unique_slug(self, slug):
        if not slug:
            return False
        candidate, n = slug, 2
        while self.with_context(active_test=False).search_count([('slug', '=', candidate)]):
            candidate, n = '%s-%s' % (slug, n), n + 1
        return candidate

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('slug'):
                vals['slug'] = self._wasm_slugify(vals['slug'])
            elif vals.get('name'):
                vals['slug'] = self._wasm_unique_slug(self._wasm_slugify(vals['name']))
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('slug'):
            vals['slug'] = self._wasm_slugify(vals['slug'])
        return super().write(vals)

    # ------------------------------------------------------------------
    # website helpers
    # ------------------------------------------------------------------
    def wasm_unique(self):
        self.ensure_one()
        return str(int(self.write_date.timestamp())) if self.write_date else '0'

    def wasm_image_url(self):
        self.ensure_one()
        return '/wasm/service/%s/image?unique=%s' % (self.id, self.wasm_unique())

    def wasm_banner_url(self):
        self.ensure_one()
        if self.banner_image:
            return '/wasm/service/%s/banner?unique=%s' % (self.id, self.wasm_unique())
        return self.wasm_image_url()

    def wasm_card_description(self):
        self.ensure_one()
        return self.card_description or self.short_description or ''

    def wasm_title(self):
        self.ensure_one()
        return self.page_title or self.name or ''

    def wasm_features(self):
        self.ensure_one()
        return [line.strip(' -•\t') for line in (self.features or '').splitlines() if line.strip(' -•\t')]

    def action_view_on_website(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_url', 'url': self.website_url, 'target': 'new'}

    def wasm_media(self):
        """Active gallery items (photos and videos) of the service page."""
        self.ensure_one()
        return self.media_ids.filtered('active').sorted(lambda m: (m.sequence, m.id))
