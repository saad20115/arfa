# -*- coding: utf-8 -*-
from odoo import models, fields, api

class WasmNews(models.Model):
    _name = 'wasm.news'
    _description = 'News & Articles - ARFA SPECIALIZED SYSTEMS'
    _order = 'sequence, date desc, id desc'

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
    ], string='Category', default='company_news', required=True)
    date = fields.Date(string='Publication Date', default=fields.Date.context_today, required=True)
    author = fields.Char(string='Author / Source', default='ARFA Engineering Team')
    image = fields.Image(string='Cover Image', max_width=1200, max_height=800)
    sequence = fields.Integer(string='Sequence Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('slug') and vals.get('name'):
                vals['slug'] = vals['name'].lower().replace(' ', '-')
        return super(WasmNews, self).create(vals_list)
