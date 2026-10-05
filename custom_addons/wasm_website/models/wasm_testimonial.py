# -*- coding: utf-8 -*-
from odoo import fields, models


class WasmTestimonial(models.Model):
    _name = 'wasm.testimonial'
    _description = 'Client Testimonial & Review - ARFA SPECIALIZED SYSTEMS'
    _order = 'sequence, id desc'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'image': 512}

    name = fields.Char(string='Client Name', required=True)
    role_or_project = fields.Char(string='Role / Project Name', help='e.g., Riyadh Commercial Tower or Residential Fitout Owner')
    rating = fields.Selection([
        ('1', '1 Star'),
        ('2', '2 Stars'),
        ('3', '3 Stars'),
        ('4', '4 Stars'),
        ('5', '5 Stars')
    ], string='Rating', default='5', required=True)
    feedback = fields.Text(string='Review Content / Feedback', required=True)
    image = fields.Image(string='Client Avatar / Logo', max_width=512, max_height=512)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    def wasm_image_url(self):
        """Public avatar URL (cache-busted), '' when no image was uploaded."""
        self.ensure_one()
        if not self.image:
            return ''
        unique = str(int(self.write_date.timestamp())) if self.write_date else '0'
        return '/wasm/testimonial/%s/image?unique=%s' % (self.id, unique)
