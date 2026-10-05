# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from .wasm_mixins import BANNER_PX, wasm_check_urls

_YOUTUBE_RE = re.compile(r'(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)([A-Za-z0-9_-]{6,})')
_VIMEO_RE = re.compile(r'vimeo\.com/(?:video/)?(\d+)')


class WasmGalleryImage(models.Model):
    _name = 'wasm.gallery.image'
    _description = 'معرض الصور والفيديو - Photo & Video Gallery'
    _order = 'sequence, id desc'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'image': BANNER_PX}

    name = fields.Char(string='العنوان / الوصف', help='يظهر كتعليق على الصورة (اختياري)')
    media_type = fields.Selection([('image', 'صورة'), ('video', 'فيديو')], string='النوع',
                                  default='image', required=True)
    image = fields.Image(string='الصورة', max_width=1920, max_height=1200,
                         help='للفيديو: صورة الغلاف التي تظهر قبل التشغيل (اختياري)')
    video_file = fields.Binary(string='ملف الفيديو (MP4)', attachment=True)
    video_filename = fields.Char(string='اسم ملف الفيديو')
    video_url = fields.Char(string='رابط الفيديو', help='رابط YouTube أو Vimeo أو رابط مباشر لملف MP4')
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
    ], string='التصنيف', default='all', required=True)
    project_id = fields.Many2one('wasm.project', string='المشروع', index=True, ondelete='set null')
    service_id = fields.Many2one('wasm.service', string='الخدمة', index=True, ondelete='set null')
    show_in_gallery = fields.Boolean(string='يظهر في معرض صفحة المشاريع', default=True,
                                     help='يظهر في قسم PHOTO GALLERY بصفحة المشاريع إذا لم يكن مرتبطاً بخدمة')
    sequence = fields.Integer(string='الترتيب', default=10)
    active = fields.Boolean(string='نشط', default=True)

    @api.constrains('media_type', 'image', 'video_file', 'video_url')
    def _check_media(self):
        for rec in self:
            if rec.media_type == 'image' and not rec.image:
                raise ValidationError('ارفع الصورة.')
            if rec.media_type == 'video' and not (rec.video_file or rec.video_url):
                raise ValidationError('ارفع ملف الفيديو أو اكتب رابطه.')

    @api.constrains('video_url')
    def _check_wasm_urls(self):
        wasm_check_urls(self, url_fields=('video_url',))

    def _wasm_unique(self):
        self.ensure_one()
        return str(int(self.write_date.timestamp())) if self.write_date else '0'

    def wasm_image_url(self):
        """Photo URL (for a video: its cover image, or '' when none)."""
        self.ensure_one()
        if not self.image:
            return ''
        return '/wasm/gallery/%s/image?unique=%s' % (self.id, self._wasm_unique())

    def wasm_is_video(self):
        self.ensure_one()
        return self.media_type == 'video'

    def wasm_video_src(self):
        """Direct playable source for <video> (uploaded MP4 or MP4 link), '' for YouTube/Vimeo."""
        self.ensure_one()
        if self.video_file:
            return '/wasm/gallery/%s/video?unique=%s' % (self.id, self._wasm_unique())
        if self.video_url and not self.wasm_video_embed():
            return self.video_url
        return ''

    def wasm_video_embed(self):
        """Embeddable iframe URL for YouTube / Vimeo links, else ''."""
        self.ensure_one()
        url = self.video_url or ''
        m = _YOUTUBE_RE.search(url)
        if m:
            return 'https://www.youtube.com/embed/%s' % m.group(1)
        m = _VIMEO_RE.search(url)
        if m:
            return 'https://player.vimeo.com/video/%s' % m.group(1)
        return ''

    def wasm_category_label(self):
        self.ensure_one()
        return dict(self._fields['category'].selection).get(self.category, '')
