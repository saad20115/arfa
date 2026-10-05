# -*- coding: utf-8 -*-
from odoo import api, fields, models

from .wasm_mixins import wasm_check_urls


class WasmPartner(models.Model):
    _name = 'wasm.partner'
    _description = 'شركاء النجاح - Our Partners'
    _order = 'sequence, id'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'logo': 600}

    name = fields.Char(string='اسم الشريك / Partner Name', required=True)
    sequence = fields.Integer(string='الترتيب / Sequence', default=10)
    logo = fields.Binary(string='شعار الشريك / Logo Image', help='قم برفع صورة شعار الشريك')
    logo_url = fields.Char(string='رابط الشعار الخارجي / External Logo URL', help='يمكنك إدخال رابط مباشر لصورة الشعار')
    website_url = fields.Char(string='رابط موقع الشريك / Partner Website URL', help='رابط الموقع الخارجي للشريك (مثال: https://www.wyndhamhotels.com)')
    description = fields.Text(string='وصف مختصر / Description')
    active = fields.Boolean(string='نشط / Active', default=True)

    @api.constrains('logo_url', 'website_url')
    def _check_wasm_urls(self):
        wasm_check_urls(self, url_fields=('logo_url', 'website_url'))

    def get_logo_src(self):
        """Returns binary endpoint URL or raw logo_url if provided."""
        self.ensure_one()
        if self.logo:
            unique = str(int(self.write_date.timestamp())) if self.write_date else '0'
            return f'/wasm/partner/{self.id}/logo?unique={unique}'
        elif self.logo_url:
            return self.logo_url
        return '/web/static/img/placeholder.png'
