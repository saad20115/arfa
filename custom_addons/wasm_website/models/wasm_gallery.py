# -*- coding: utf-8 -*-
from odoo import models, fields


class WasmGalleryImage(models.Model):
    _name = 'wasm.gallery.image'
    _description = 'Photo & Media Gallery - ARFA SPECIALIZED SYSTEMS'
    _order = 'sequence, id desc'

    name = fields.Char(string='Photo Title / Caption', required=True)
    image = fields.Image(string='Photo File', max_width=1920, max_height=1200, required=True)
    category = fields.Selection([
        ('all', 'All Divisions'),
        ('exterior', 'Exterior View'),
        ('interior', 'Interior Spaces'),
        ('site', 'Site Progress'),
        ('civil', 'Structural & Civil'),
        ('mep', 'MEP & HVAC'),
        ('steel', 'Modern Building Systems'),
        ('mep_medical', 'Medical Gas Systems'),
        ('interiors', 'Fitouts & Architecture'),
    ], string='Division Category', default='all', required=True)
    project_id = fields.Many2one('wasm.project', string='Associated Project', index=True, ondelete='set null')
    sequence = fields.Integer(string='Sequence Order', default=10)
    active = fields.Boolean(string='Active', default=True)

    def wasm_image_url(self):
        self.ensure_one()
        unique = str(int(self.write_date.timestamp())) if self.write_date else '0'
        return '/wasm/gallery/%s/image?unique=%s' % (self.id, unique)

    def wasm_category_label(self):
        self.ensure_one()
        return dict(self._fields['category'].selection).get(self.category, '')
