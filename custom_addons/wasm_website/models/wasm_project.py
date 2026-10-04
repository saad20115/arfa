# -*- coding: utf-8 -*-
from odoo import models, fields


class WasmProject(models.Model):
    _name = 'wasm.project'
    _description = 'مشاريع شركة عرفة الهندسية'
    _order = 'sequence, id desc'

    name = fields.Char(string='اسم المشروع', required=True, translate=True)
    sequence = fields.Integer(string='التسلسل', default=10)
    image = fields.Image(string='صورة المشروع الرئيسية', max_width=1920, max_height=1200)
    description = fields.Text(string='وصف مختصر للمشروع', translate=True)
    detailed_description = fields.Html(string='التفاصيل الهندسية والفنية للمشروع', translate=True)
    video_url = fields.Char(string='رابط فيديو المشروع (MP4 / YouTube)', help='رابط مقطع فيديو استعراضي للمشروع')
    attachment_ids = fields.Many2many('ir.attachment', string='معرض صور وفيديوهات المشروع')

    state = fields.Selection([
        ('in_progress', 'تحت التنفيذ'),
        ('completed', 'مكتمل بنجاح'),
    ], string='حالة المشروع', default='completed', required=True)

    project_type = fields.Selection([
        ('commercial', 'أبراج ومشاريع تجارية'),
        ('residential', 'مجمعات سكنية وفلل'),
        ('mep', 'أعمال كهروميكانيكية وتكييف'),
        ('infrastructure', 'بناء عظم وبنية تحتية'),
    ], string='نوع المشروع', default='commercial', required=True)

    location = fields.Char(string='موقع المشروع (المدينة/المحافظة)', required=True, translate=True)
    client_name = fields.Char(string='الجهة المترأسة / المالك', translate=True)
    area = fields.Float(string='المساحة المنفذة (م²)')
    completion_date = fields.Date(string='تاريخ التسليم / الإنجاز')
    active = fields.Boolean(string='نشط للموقع', default=True)

    # --- "Project at a glance" facts card ---
    scope_of_work = fields.Char(string='دور عرفة في المشروع', translate=True,
                                help='مثال: تصميم وتنفيذ، أعمال كهروميكانيكية، إدارة مشروع')
    brand_operator = fields.Char(string='العلامة / المشغّل', translate=True, help='مثال: Accor Hotels Group')
    building_config = fields.Char(string='تكوين المبنى / الأدوار', help='مثال: B+G+M+14')
    units_count = fields.Char(string='عدد الوحدات / الغرف', help='مثال: 232 غرفة')
    facilities = fields.Char(string='المرافق', translate=True, help='مثال: مطاعم، نادي رياضي، مسبح')

    # --- Collapsible sections ---
    address = fields.Char(string='العنوان التفصيلي', translate=True)
    building_type = fields.Char(string='نوع المبنى', translate=True, help='مثال: برج فندقي 4 نجوم')
    floor_breakdown = fields.Text(
        string='توزيع الأدوار / مكونات المشروع', translate=True,
        help='سطر لكل بند بصيغة: البند: الوصف\nمثال:\nالدور الأرضي: الاستقبال والردهة\nالدور الأول: قاعات الاجتماعات')
    deliverables = fields.Html(string='نطاق العمل والمخرجات', translate=True,
                               help='الأعمال التي نفذتها عرفة في المشروع')

    gallery_image_ids = fields.One2many('wasm.gallery.image', 'project_id', string='صور المشروع حسب الأقسام')

    # ------------------------------------------------------------------
    # Helpers for the website templates
    # ------------------------------------------------------------------
    def wasm_unique(self):
        self.ensure_one()
        return str(int(self.write_date.timestamp())) if self.write_date else '0'

    def wasm_main_image_url(self):
        self.ensure_one()
        return '/wasm/project/%s/image?unique=%s' % (self.id, self.wasm_unique())

    _TYPE_EN = {
        'commercial': 'Commercial & Towers',
        'residential': 'Residential',
        'mep': 'MEP & HVAC',
        'infrastructure': 'Structure & Infrastructure',
    }
    _STATE_EN = {'completed': 'Completed', 'in_progress': 'In progress'}

    def wasm_type_label(self, is_en=False):
        self.ensure_one()
        if is_en:
            return self._TYPE_EN.get(self.project_type, '')
        return dict(self._fields['project_type'].selection).get(self.project_type, '')

    def wasm_state_label(self, is_en=False):
        self.ensure_one()
        if is_en:
            return self._STATE_EN.get(self.state, '')
        return dict(self._fields['state'].selection).get(self.state, '')

    def wasm_floor_rows(self):
        """floor_breakdown lines -> [(label, value)]; a line without ':' becomes a sub-heading."""
        self.ensure_one()
        rows = []
        for line in (self.floor_breakdown or '').splitlines():
            line = line.strip()
            if not line:
                continue
            for sep in (':', '：'):
                if sep in line:
                    label, value = line.split(sep, 1)
                    rows.append((label.strip(), value.strip()))
                    break
            else:
                rows.append((line, ''))
        return rows

    def wasm_gallery_items(self):
        """Gallery entries: categorized gallery photos, then images uploaded in the media tab."""
        self.ensure_one()
        items = []
        for img in self.gallery_image_ids.filtered('active').sorted(lambda r: (r.sequence, r.id)):
            items.append({
                'url': img.wasm_image_url(),
                'caption': img.name or '',
                'cat': img.category or 'all',
                'cat_label': img.wasm_category_label() if img.category != 'all' else '',
            })
        for att in self.sudo().attachment_ids.filtered(lambda a: (a.mimetype or '').startswith('image/')):
            items.append({
                'url': '/wasm/project/%s/media/%s?unique=%s' % (self.id, att.id, att.checksum or '0'),
                'caption': att.name or '',
                'cat': 'all',
                'cat_label': '',
            })
        return items

    def wasm_gallery_categories(self):
        """Filter tabs: only categories that actually have photos."""
        self.ensure_one()
        seen, cats = set(), []
        for item in self.wasm_gallery_items():
            if item['cat'] != 'all' and item['cat'] not in seen:
                seen.add(item['cat'])
                cats.append({'key': item['cat'], 'label': item['cat_label']})
        return cats

    def wasm_neighbors(self):
        """(previous, next) active projects in website order, wrapping around."""
        self.ensure_one()
        projects = self.sudo().search([('active', '=', True)], order='sequence, id desc')
        ids = projects.ids
        if self.id not in ids or len(ids) < 2:
            return self.browse(), self.browse()
        i = ids.index(self.id)
        return projects[i - 1], projects[(i + 1) % len(ids)]
