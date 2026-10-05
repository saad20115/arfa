# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools import is_html_empty
from odoo.tools.misc import format_date

from .wasm_mixins import CARD_PX, wasm_check_urls

# Arabic labels of the categories (the selection labels below are the English ones).
CATEGORY_AR = {
    'company_news': 'أخبار الشركة',
    'engineering': 'الهندسة والإنشاءات',
    'sustainability': 'الاستدامة وكود البناء',
    'events': 'الفعاليات والمعارض',
    'projects': 'إنجازات المشاريع',
    'safety': 'السلامة والامتثال',
    'quality': 'الجودة والمعايير',
}

# Colour of the category badge on the website cards.
CATEGORY_BADGE_CLASS = {
    'company_news': 'bg-info text-dark',
    'engineering': 'bg-primary text-white',
    'sustainability': 'bg-warning text-dark',
    'events': 'bg-dark text-white',
    'projects': 'bg-warning text-dark',
    'safety': 'bg-success text-white',
    'quality': 'bg-secondary text-white',
}


class WasmNews(models.Model):
    _name = 'wasm.news'
    _description = 'News & Articles - ARFA SPECIALIZED SYSTEMS'
    _order = 'sequence, date desc, id desc'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'image': CARD_PX}

    name = fields.Char(string='Article Title', required=True)
    slug = fields.Char(string='URL Slug')
    summary = fields.Text(string='Article Summary', help='Short summary displayed on news listing card')
    content = fields.Html(string='Full Article Content', help='Rich text content for full article body')

    # Bilingual fields used by the website templates (the templates expected them but they
    # did not exist, so /news crashed as soon as an article was published).
    title_en = fields.Char(string='Article Title (English)')
    summary_ar = fields.Text(related='summary', readonly=False, string='Summary (Arabic)')
    summary_en = fields.Text(string='Summary (English)')
    content_ar = fields.Html(related='content', readonly=False, string='Content (Arabic)')
    content_en = fields.Html(string='Content (English)')
    image_url = fields.Char(string='External Image URL', help='Used only when no cover image is uploaded')
    category = fields.Selection([
        ('company_news', 'Company News'),
        ('engineering', 'Engineering & Construction'),
        ('sustainability', 'Sustainability & SBC'),
        ('events', 'Events & Exhibitions'),
        ('projects', 'Project Milestones'),
        ('safety', 'Safety & Compliance'),
        ('quality', 'Quality & Standards'),
    ], string='Category', default='company_news', required=True)
    badge_en = fields.Char(string='Badge Text (English)',
                           help='Optional text of the badge on the website card. Empty = category name.')
    badge_ar = fields.Char(string='Badge Text (Arabic)',
                           help='نص الشارة على بطاقة الخبر (اختياري). إذا ترك فارغاً يظهر اسم التصنيف.')
    date = fields.Date(string='Publication Date', default=fields.Date.context_today, required=True)
    author = fields.Char(string='Author / Source', default='ARFA Engineering Team')
    image = fields.Image(string='Cover Image', max_width=1200, max_height=800)
    sequence = fields.Integer(string='Sequence Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.constrains('image_url')
    def _check_wasm_urls(self):
        wasm_check_urls(self, url_fields=('image_url',))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug') and vals.get('name'):
                vals['slug'] = vals['name'].lower().replace(' ', '-')
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Website helpers (language-aware, used by the QWeb templates)
    # ------------------------------------------------------------------
    def _wasm_is_en(self):
        return (self.env.lang or 'en_US').startswith('en')

    def wasm_title(self):
        self.ensure_one()
        if self._wasm_is_en():
            return self.title_en or self.name or ''
        return self.name or self.title_en or ''

    def wasm_summary(self):
        self.ensure_one()
        if self._wasm_is_en():
            return self.summary_en or self.summary or ''
        return self.summary or self.summary_en or ''

    def wasm_content(self):
        """Full article body (Html) for the visitor language, falling back to the other
        language and finally to the summary (plain text)."""
        self.ensure_one()
        first, second = (self.content_en, self.content) if self._wasm_is_en() else (self.content, self.content_en)
        for html in (first, second):
            if html and not is_html_empty(html):
                return html
        return self.wasm_summary()

    def wasm_category_label(self):
        self.ensure_one()
        if not self.category:
            return ''
        if not self._wasm_is_en() and self.category in CATEGORY_AR:
            return CATEGORY_AR[self.category]
        return dict(self._fields['category']._description_selection(self.env)).get(self.category, '')

    def wasm_badge(self):
        """Text of the badge on the website (custom badge text, else category label)."""
        self.ensure_one()
        custom = self.badge_en if self._wasm_is_en() else self.badge_ar
        return custom or self.wasm_category_label()

    def wasm_badge_class(self):
        self.ensure_one()
        return CATEGORY_BADGE_CLASS.get(self.category, 'bg-warning text-dark')

    def wasm_date_label(self):
        """Publication date as shown on the website, e.g. '15 Aug 2026'."""
        self.ensure_one()
        if not self.date:
            return ''
        return format_date(self.env, self.date, date_format='dd MMM y')

    def wasm_image_src(self):
        """Cover image URL (uploaded image, else external URL, else '')."""
        self.ensure_one()
        if self.image:
            unique = str(int(self.write_date.timestamp())) if self.write_date else '0'
            return '/wasm/news/%s/image?unique=%s' % (self.id, unique)
        return self.image_url or ''
