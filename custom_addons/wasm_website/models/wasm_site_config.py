# -*- coding: utf-8 -*-
import hashlib
import hmac
import json
import logging
import re
import time

from markupsafe import Markup

from odoo import api, fields, models
from odoo.http import request

from .texts.t_seo import PAGE_IDS
from .wasm_mixins import BANNER_PX, wasm_check_urls

HIDE_FROM_SEARCH_PARAM = 'wasm_website.hide_from_search_engines'
FORM_TOKEN_MIN_AGE = 3              # seconds: faster than a human can fill the form
FORM_TOKEN_MAX_AGE = 24 * 3600      # a page left open for a day must be reloaded
META_DESCRIPTION_MAX = 155

_logger = logging.getLogger(__name__)

# Arabic content used as the default of every *_ar field (and by the 19.0.1.1.0
# migration to fill Arabic fields that were saved with the old English defaults).
AR_DEFAULTS = {
    'showcase_title_ar': 'نبني رؤية البنية التحتية للمملكة العربية السعودية',
    'showcase_desc_ar': 'شاهد كيف تنفّذ شركة عرفة للأنظمة المتخصصة المشاريع الإنشائية والتجارية الكبرى وفق كود البناء السعودي ومعايير جودة صارمة.',
    'showcase_bullet1_ar': 'تنفيذ ملتزم بالكامل بكود البناء السعودي (SBC 301-306).',
    'showcase_bullet2_ar': 'هندسة كهروميكانيكية متكاملة: تكييف، إطفاء حريق، وشبكات كهربائية.',
    'showcase_bullet3_ar': 'فريق مهندسين معتمد من الهيئة السعودية للمهندسين.',
    'hero_title_ar': 'التميّز الهندسي وحلول الإنشاء المتكاملة',
    'contact_address_ar': 'الرياض - حي الصحافة - طريق الملك فهد',
    'contact_working_hours_ar': 'الأحد - الخميس: 8:00 ص - 5:00 م',
    'pillar1_title_ar': 'المقاولات الإنشائية والمدنية',
    'pillar1_desc_ar': 'الهياكل الخرسانية والأساسات والأعمال الإنشائية الثقيلة المنفذة وفق كود البناء السعودي.',
    'pillar2_title_ar': 'الأنظمة الكهروميكانيكية MEP',
    'pillar2_desc_ar': 'مجاري التكييف المتقدمة، السباكة، شبكات الكهرباء، وأنظمة التحكم الذكي.',
    'pillar3_title_ar': 'تسليم المشاريع مفتاح باليد',
    'pillar3_desc_ar': 'إدارة هندسية شاملة وتشطيبات داخلية وتسليم متكامل للمشروع من البداية حتى النهاية.',
    'stat1_label_ar': 'مشروع مكتمل',
    'stat2_label_ar': 'عاماً من الخبرة',
    'stat3_label_ar': 'م² مساحة منفذة',
    'stat4_label_ar': 'مهندس ومتخصص',
    'why1_title_ar': 'الالتزام بكود البناء السعودي',
    'why1_desc_ar': 'التزام صارم بمواصفات كود البناء السعودي في جميع الأعمال الخرسانية والإنشائية.',
    'why2_title_ar': 'تقنيات BIM ثلاثية الأبعاد',
    'why2_desc_ar': 'نمذجة ثلاثية الأبعاد متقدمة وكشف التعارضات قبل التنفيذ في الموقع لضمان صفر أخطاء.',
    'why3_title_ar': 'معدات ثقيلة مملوكة',
    'why3_desc_ar': 'أسطول متكامل من الحفارات والرافعات ومضخات الخرسانة لتسريع الجداول الزمنية.',
    'why4_title_ar': 'التزام صارم بالمواعيد',
    'why4_desc_ar': 'ضمان إنجاز المشروع ضمن الجدول المتفق عليه وبميزانية شفافة.',
    'why5_title_ar': 'مختبر جودة معتمد',
    'why5_desc_ar': 'اختبارات دقيقة للعينات وفحص مقاومة الخرسانة بالموجات فوق الصوتية في الموقع.',
    'why6_title_ar': 'الأيزو والسلامة في المواقع',
    'why6_desc_ar': 'سياسات بيئة عمل خالية من المخاطر وفق أطر السلامة الدولية.',
    'srv1_title_ar': 'أنظمة البناء الحديثة',
    'srv1_desc_ar': 'تقنيات البناء الحديثة، الواجهات الزجاجية، الهياكل المعدنية مسبقة الصنع، والتشطيبات المتكاملة.',
    'srv2_title_ar': 'الأنظمة الكهروميكانيكية',
    'srv2_desc_ar': 'تصميم وتوريد وتركيب شبكات الكهرباء والبنية الميكانيكية وشبكات الصرف الصحي.',
    'srv3_title_ar': 'أنظمة المباني الذكية',
    'srv3_desc_ar': 'أتمتة المباني، لوحات التحكم الذكية، الأنظمة الأمنية، وتقنيات الإنذار المبكر.',
    'srv4_title_ar': 'حلول الطاقة البديلة',
    'srv4_desc_ar': 'أنظمة الطاقة الشمسية الكهروضوئية وحلول ترشيد الطاقة للقطاعات التجارية.',
    'srv5_title_ar': 'أنظمة الحماية والوقاية من الحريق',
    'srv5_desc_ar': 'أنظمة الإطفاء التلقائي، شبكات الإنذار، وتركيب مضخات معتمدة من الدفاع المدني.',
    'srv6_title_ar': 'أنظمة الغازات الطبية',
    'srv6_desc_ar': 'تصميم وتركيب خطوط الغازات الطبية المركزية والبنية التحتية لغرف العمليات.',
    'srv7_title_ar': 'تطوير البنية التحتية',
    'srv7_desc_ar': 'الأنابيب الأرضية، شبكات التصريف، أعمال الحفر، وأعمال البنية التحتية العامة.',
    'srv8_title_ar': 'التخطيط والإنشاءات',
    'srv8_desc_ar': 'الهياكل الخرسانية والأساسات والأعمال الإنشائية الثقيلة المنفذة وفق كود البناء السعودي.',
}

# Static images used when nothing was uploaded in the backend.
DEFAULT_IMAGES = {
    'pillar1_img': '/wasm_website/static/src/img/pillar_civil.jpg',
    'pillar2_img': '/wasm_website/static/src/img/pillar_mep.jpg',
    'pillar3_img': '/wasm_website/static/src/img/pillar_mgmt.jpg',
    'why1_img': '/wasm_website/static/src/img/why_sbc.jpg',
    'why2_img': '/wasm_website/static/src/img/why_bim.jpg',
    'why3_img': '/wasm_website/static/src/img/why_machinery.jpg',
    'why4_img': '/wasm_website/static/src/img/why_timelines.jpg',
    'why5_img': '/wasm_website/static/src/img/why_qc.jpg',
    'why6_img': '/wasm_website/static/src/img/why_safety.jpg',
    'srv1_img': '/wasm_website/static/src/img/arfa_exhibition_building.webp',
    'srv2_img': '/wasm_website/static/src/img/arfa_electrical_panels.webp',
    'srv3_img': '/wasm_website/static/src/img/service_card_3.jpg',
    'srv4_img': '/wasm_website/static/src/img/service_card_4.jpg',
    'srv5_img': '/wasm_website/static/src/img/service_card_5.jpg',
    'srv6_img': '/wasm_website/static/src/img/service_card_6.jpg',
    'srv7_img': '/wasm_website/static/src/img/service_card_7.jpg',
    'srv8_img': '/wasm_website/static/src/img/service_card_8.jpg',
    'hero_bg_image': '/wasm_website/static/src/img/hero_bg.jpg',
    'showcase_poster': '',
    'showcase_bg_image': '',
    'about_image': '/wasm_website/static/src/img/about_teamwork.jpg',
    'footer_logo': '/wasm_website/static/src/img/arfa_logo_stacked.svg',
}


def _ar(name):
    return AR_DEFAULTS.get(name, '')


def one_line(text):
    """Single line text: collapsed whitespace, no space before punctuation ('Jeddah , KSA' -> 'Jeddah, KSA')."""
    return re.sub(r'\s+([,،.;:])', r'\1', ' '.join((text or '').split()))


class WasmSiteConfig(models.Model):
    _name = 'wasm.site.config'
    _description = 'Site Config & Media Settings - ARFA SPECIALIZED SYSTEMS'
    _inherit = ['wasm.image.mixin']
    _wasm_image_fields = {'showcase_poster': BANNER_PX, 'showcase_bg_image': BANNER_PX, 'hero_bg_image': BANNER_PX,
                          'about_image': BANNER_PX, 'footer_logo': 800}

    name = fields.Char(string='Config Name', default='Official Website Config', required=True)

    # Display Limit & Section Toggle Controls
    home_projects_limit = fields.Integer(string='Homepage Projects Limit', default=6, help='Maximum number of projects displayed on homepage')
    projects_page_limit = fields.Integer(string='Projects Page Limit', default=12, help='Maximum number of projects displayed on projects page')
    show_testimonials = fields.Boolean(string='Show Client Testimonials Section', default=True, help='Toggle to display or hide the "What Our Clients Say" section on the homepage.')

    # Showcase Video & Content Settings
    showcase_video_file = fields.Binary(string='Vision Showcase Video (MP4)', attachment=True, help='Upload custom MP4 video file for hero showcase')
    showcase_video_filename = fields.Char(string='Video Filename')
    showcase_video_url = fields.Char(string='Video URL / Path', default='/wasm_website/static/src/video/hero_construction.mp4', help='External video URL or default static path')
    showcase_poster = fields.Image(string='Video Poster Cover', max_width=1920, max_height=1080, help='Cover image before video starts')

    showcase_title_ar = fields.Char(string='Showcase Title (Arabic)', default=_ar('showcase_title_ar'))
    showcase_title_en = fields.Char(string='Showcase Title (English)', default="Building Saudi Arabia's Infrastructure Vision")
    showcase_desc_ar = fields.Text(string='Showcase Description (Arabic)', default=_ar('showcase_desc_ar'))
    showcase_desc_en = fields.Text(string='Showcase Description (English)', default='Watch how ARFA SPECIALIZED SYSTEMS executes major structural and commercial development projects adhering to Saudi Building Code and strict quality metrics.')

    showcase_bullet1_ar = fields.Char(string='Bullet 1 (Arabic)', default=_ar('showcase_bullet1_ar'))
    showcase_bullet1_en = fields.Char(string='Bullet 1 (English)', default='Execution strictly adhering to Saudi Building Code (SBC 301-306).')
    showcase_bullet2_ar = fields.Char(string='Bullet 2 (Arabic)', default=_ar('showcase_bullet2_ar'))
    showcase_bullet2_en = fields.Char(string='Bullet 2 (English)', default='Complete MEP engineering: HVAC, fire fighting, and electrical networks.')
    showcase_bullet3_ar = fields.Char(string='Bullet 3 (Arabic)', default=_ar('showcase_bullet3_ar'))
    showcase_bullet3_en = fields.Char(string='Bullet 3 (English)', default='Certified team of engineers accredited by the Saudi Council of Engineers.')

    showcase_bg_image = fields.Image(string='Showcase Background Image', max_width=1920, max_height=1080)

    # Hero Banner Settings (subtitle under the company name + poster of the hero video)
    hero_title_ar = fields.Char(string='Hero Subtitle (Arabic)', default=_ar('hero_title_ar'))
    hero_title_en = fields.Char(string='Hero Subtitle (English)', default='Pioneering Engineering & Construction Excellence')
    hero_bg_image = fields.Image(string='Hero Background / Video Poster', max_width=1920, max_height=1080)

    # Homepage hero background video
    home_hero_video_file = fields.Binary(string='Homepage Hero Video (MP4)', attachment=True)
    home_hero_video_filename = fields.Char(string='Hero Video Filename')
    home_hero_video_url = fields.Char(string='Hero Video URL / Path', default='/wasm_website/static/src/video/hero_construction.mp4',
                                      help='Used when no file is uploaded: an MP4 link or a module path')

    # Page images
    about_image = fields.Image(string='About Page Image', max_width=1920, max_height=1400)
    footer_logo = fields.Image(string='Footer Logo', max_width=800, max_height=800,
                               help='Leave empty to use the default ARFA logo')

    # Maps (Google Maps "Embed a map" link = the src="..." of the iframe)
    map_embed_url = fields.Char(string='Location Page Map (embed URL)',
                                default='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d115923.63388726593!2d46.6752957!3d24.7135517!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x3e2f03890d489399%3A0xba974d1c98e79fd5!2sRiyadh%20Saudi%20Arabia!5e0!3m2!1sen!2ssa!4v1690000000000!5m2!1sen!2ssa')
    map_link_url = fields.Char(string='Location Page "Get Directions" link',
                               default='https://maps.google.com/?q=24.7135517,46.6752957')
    hq_map_embed_url = fields.Char(string='Head Office Map (embed URL)',
                                   default='https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3711.4798363803156!2d39.1809849!3d21.5280852!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x15c3cfc490b3441f%3A0xc4a4b5005a01fcc0!2z2YXYsdmD2LIg2KfZhNiu2YTZitisINmD2LnZg9mK!5e0!3m2!1sar!2ssa!4v1786653012903!5m2!1sar!2ssa')
    hq_map_link_url = fields.Char(string='Head Office "Get Directions" link',
                                  default='https://maps.google.com/?q=21.5280852,39.1809849')

    # Company Profile PDF Document
    company_profile_pdf = fields.Binary(string='Company Profile PDF Document', attachment=True, help='Upload official company profile PDF file')
    company_profile_filename = fields.Char(string='Company Profile Filename', default='Arfa_Company_Profile_2026.pdf')

    # Contact Info Settings
    contact_phone = fields.Char(string='Official Phone', default='+966 11 234 5678')
    contact_phone_secondary = fields.Char(string='Mobile / WhatsApp', default='+966 54 543 2343')
    contact_email = fields.Char(string='Official Email', default='info@arfa-sa.com')
    contact_address_ar = fields.Char(string='Address (Arabic)', default=_ar('contact_address_ar'))
    contact_address_en = fields.Char(string='Address (English)', default='Riyadh - Al Sahafa District - King Fahd Road')
    contact_working_hours_ar = fields.Char(string='Working Hours (Arabic)', default=_ar('contact_working_hours_ar'))
    contact_working_hours_en = fields.Char(string='Working Hours (English)', default='Sun - Thu: 8:00 AM - 5:00 PM')

    # Email Server & Notification Settings
    target_notification_email = fields.Char(
        string='البريد المستهدف لاستقبال الإشعارات',
        default='info@arfa-sa.com',
        help='البريد الإلكتروني الذي تصل إليه إشعارات طلبات التسعير والاتصال الجديدة من الموقع الإلكتروني'
    )
    enable_email_notifications = fields.Boolean(
        string='تفعيل إرسال إشعارات البريد للإدارة',
        default=True,
        help='عند التفعيل سيتم إرسال رسالة بريد إلكترونية فورية للبريد المستهدف عند تعبئة أي نموذج'
    )
    enable_customer_confirmation_email = fields.Boolean(
        string='إرسال بريد تأكيد تلقائي للعميل بالرقم المرجعي',
        default=True,
        help='إرسال بريد إلكتروني تلقائي للعميل يتضمن الرقم المرجعي المميز وتأكيد استلام الطلب'
    )

    # Brand & search engines (SEO / AI search)
    brand_name_en = fields.Char(string='Company Name (English)', default='ARFA Construction & Specialized Systems')
    brand_name_ar = fields.Char(string='Company Name (Arabic)', default='شركة عرفة للأنظمة المتخصصة')
    founding_year = fields.Char(string='Founded (year)', default='1972')
    seo_description_en = fields.Text(
        string='Website Description for Google (English)',
        default='ARFA Construction & Specialized Systems is a Saudi engineering and construction contractor delivering '
                'structural works, electromechanical (MEP) systems, smart building automation, fire protection, '
                'medical gas, alternative energy and infrastructure projects to the Saudi Building Code.',
        help='Shown by Google and AI assistants when a page has no description of its own (about 150 characters is ideal).')
    seo_description_ar = fields.Text(
        string='Website Description for Google (Arabic)',
        default='شركة عرفة للأنظمة المتخصصة: مقاول هندسي وإنشائي سعودي ينفذ الأعمال الإنشائية والأنظمة الكهروميكانيكية '
                'والمباني الذكية وأنظمة الحريق والغازات الطبية والطاقة البديلة والبنية التحتية وفق كود البناء السعودي.')
    service_area = fields.Char(string='Service Area', default='Kingdom of Saudi Arabia',
                               help='Regions/cities served, e.g. Riyadh, Jeddah, Makkah, Eastern Province')

    # Social media links (footer icons + Google knowledge panel)
    social_linkedin = fields.Char(string='LinkedIn URL')
    social_x = fields.Char(string='X (Twitter) URL')
    social_instagram = fields.Char(string='Instagram URL')
    social_facebook = fields.Char(string='Facebook URL')
    social_youtube = fields.Char(string='YouTube URL')
    social_tiktok = fields.Char(string='TikTok URL')
    social_snapchat = fields.Char(string='Snapchat URL')

    # Trial / staging switch (also set directly by the deployment scripts)
    hide_from_search_engines = fields.Boolean(
        string='إخفاء الموقع عن محركات البحث (وضع التجربة)',
        compute='_compute_hide_from_search_engines', inverse='_inverse_hide_from_search_engines',
        help='robots.txt يمنع الفهرسة ويضاف وسم noindex لكل الصفحات. أوقفه عند تشغيل الموقع على النطاق الرسمي.')

    _URL_FIELDS = ('social_linkedin', 'social_x', 'social_instagram', 'social_facebook', 'social_youtube',
                   'social_tiktok', 'social_snapchat', 'showcase_video_url', 'home_hero_video_url',
                   'map_link_url', 'hq_map_link_url')
    _EMBED_FIELDS = ('map_embed_url', 'hq_map_embed_url')

    @api.constrains(*_URL_FIELDS, *_EMBED_FIELDS)
    def _check_wasm_urls(self):
        wasm_check_urls(self, url_fields=self._URL_FIELDS, embed_fields=self._EMBED_FIELDS)

    def _compute_hide_from_search_engines(self):
        value = self.wasm_hide_from_search()
        for rec in self:
            rec.hide_from_search_engines = value

    def _inverse_hide_from_search_engines(self):
        for rec in self[:1]:
            self.env['ir.config_parameter'].sudo().set_param(
                HIDE_FROM_SEARCH_PARAM, 'True' if rec.hide_from_search_engines else 'False')

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------
    @api.model
    def get_config(self):
        """Return THE website configuration record.

        The previous implementation deleted every record except the newest one
        on each page view. Pressing "New" once in the backend form therefore
        created an empty record and the next website visit silently deleted the
        real configuration (texts + uploaded images). Now the oldest record is
        always the official one and nothing is ever deleted here; a record is
        only created when none exists at all.
        """
        config = self.sudo().search([], order='id asc', limit=1)
        if not config:
            config = self.sudo().create({})
        return config

    @api.model
    def action_open_config(self):
        """Open the singleton config record directly in the backend."""
        config = self.get_config()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Website Config & Media Settings',
            'res_model': 'wasm.site.config',
            'res_id': config.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_view_website(self):
        """Open the homepage in a new tab to check the changes just saved."""
        return {'type': 'ir.actions.act_url', 'url': '/', 'target': 'new'}

    # ------------------------------------------------------------------
    # Helpers used by the QWeb templates
    # ------------------------------------------------------------------
    def is_en(self):
        return (self.env.lang or 'en_US').startswith('en')

    def tx(self, key):
        """Editable website text (``wasm.text``) for the visitor language."""
        return self.env['wasm.text'].sudo().get_text(key, self.env.lang)

    def txb(self, key):
        """Same as tx() but keeps line breaks (Markup with <br/>), for paragraphs."""
        return self.env['wasm.text'].sudo().get_text_br(key, self.env.lang)

    def items(self, section, limit=None):
        """Active ``wasm.content.item`` records of a section, in display order."""
        return self.env['wasm.content.item'].sudo().search(
            [('section', '=', section), ('active', '=', True)], order='sequence, id', limit=limit)

    def home_services(self):
        return self.env['wasm.service'].sudo().search(
            [('active', '=', True), ('show_on_home', '=', True)], order='sequence, id')

    def wasm_hero_video_url(self):
        self.ensure_one()
        if self.home_hero_video_file:
            return '/wasm/video/hero?unique=%s' % self.wasm_unique()
        return self.home_hero_video_url or '/wasm_website/static/src/video/hero_construction.mp4'

    def wasm_t(self, base, is_en=None):
        """Bilingual value of ``<base>_en`` / ``<base>_ar`` for the visitor language.

        Falls back to the other language when the requested one is empty, so a
        field filled in only one language still shows something.
        """
        self.ensure_one()
        if is_en is None:
            is_en = (self.env.lang or 'en_US').startswith('en')
        first, second = ('_en', '_ar') if is_en else ('_ar', '_en')
        for suffix in (first, second):
            name = base + suffix
            if name in self._fields and self[name]:
                return self[name]
        return ''

    def wasm_unique(self):
        """Cache-busting token: changes every time the record is saved."""
        self.ensure_one()
        return str(int(self.write_date.timestamp())) if self.write_date else '0'

    def wasm_img_url(self, field_name):
        """Public URL for an image field of the config.

        Uploaded image -> streamed through the module route with a ?unique=
        token (the browser caches it for a year and fetches the new one right
        after a change). Nothing uploaded -> the bundled static default image.
        """
        self.ensure_one()
        if field_name in self._fields and self[field_name]:
            return '/wasm/config/image/%s?unique=%s' % (field_name, self.wasm_unique())
        return DEFAULT_IMAGES.get(field_name, '')

    def wasm_video_url(self):
        """URL of the showcase video (uploaded file first, then the URL field)."""
        self.ensure_one()
        if self.showcase_video_file:
            return '/wasm/video/showcase?unique=%s' % self.wasm_unique()
        return self.showcase_video_url or '/wasm_website/static/src/video/hero_construction.mp4'

    # ------------------------------------------------------------------
    # SEO / AI search helpers
    # ------------------------------------------------------------------
    def wasm_site_description(self, is_en=True):
        self.ensure_one()
        return (self.seo_description_en if is_en else self.seo_description_ar) or self.seo_description_en or ''

    @api.model
    def wasm_hide_from_search(self):
        """True while the site must stay out of search engines (trial / staging).

        Read straight from the table (not the cached get_param): the deployment scripts
        switch it with SQL and the change must apply at once, in every worker.
        """
        self.env['ir.config_parameter'].flush_model(['key', 'value'])
        self.env.cr.execute("SELECT value FROM ir_config_parameter WHERE key = %s", (HIDE_FROM_SEARCH_PARAM,))
        row = self.env.cr.fetchone()
        return bool(row) and str(row[0] or '').strip().lower() in ('true', '1', 'yes')

    @api.model
    def wasm_base_url(self, url_root=None):
        """Public site address without trailing slash.

        Taken from the ``web.base.url`` system parameter, never from the request Host
        header (which a client can forge). ``url_root`` is only a fallback when the
        parameter is empty.
        """
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url') or url_root or ''
        return base.strip().rstrip('/')

    @staticmethod
    def wasm_phone_digits(phone):
        """Saudi phone number as international digits: '+966 05x', '05x', '00966 5x' -> '9665x...'."""
        digits = ''.join(ch for ch in (phone or '') if ch.isdigit() and ch.isascii())
        if digits.startswith('00'):
            digits = digits[2:]
        if digits.startswith('9660'):          # +966 05x... typed with the local leading 0
            digits = '966' + digits[4:]
        elif digits.startswith('0') and len(digits) == 10:   # 05x mobile / 01x landline
            digits = '966' + digits[1:]
        return digits

    @api.model
    def wasm_phone_e164(self, phone):
        """E.164 form (``+966545432343``) of a phone number, '' when there are no digits."""
        digits = self.wasm_phone_digits(phone)
        return '+' + digits if digits else ''

    # ------------------------------------------------------------------
    # Anti-bot token of the public forms
    # ------------------------------------------------------------------
    @api.model
    def _wasm_form_signature(self, timestamp):
        secret = self.env['ir.config_parameter'].sudo().get_param('database.secret') or ''
        return hmac.new(secret.encode(), str(timestamp).encode(), hashlib.sha256).hexdigest()[:32]

    @api.model
    def wasm_form_token(self):
        """Signed '<unix time>.<signature>' rendered in a hidden input of the public forms."""
        timestamp = int(time.time())
        return '%s.%s' % (timestamp, self._wasm_form_signature(timestamp))

    @api.model
    def wasm_check_form_token(self, token, now=None):
        """True when ``token`` was issued by wasm_form_token() between 3 s and 24 h ago."""
        if not token or not isinstance(token, str) or len(token) > 64:
            return False
        timestamp, _sep, signature = token.strip().partition('.')
        if not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 12 or not signature:
            return False
        age = (now if now is not None else time.time()) - int(timestamp)
        if not FORM_TOKEN_MIN_AGE <= age <= FORM_TOKEN_MAX_AGE:
            return False
        return hmac.compare_digest(signature.encode(), self._wasm_form_signature(int(timestamp)).encode())

    @staticmethod
    def _wasm_shorten(text, limit=META_DESCRIPTION_MAX):
        text = ' '.join((text or '').split())
        if len(text) <= limit:
            return text
        cut = text[:limit - 1]
        if ' ' in cut[limit // 2:]:
            cut = cut.rsplit(' ', 1)[0]
        return cut.rstrip(' ,;:.-–—|') + '…'

    def _wasm_absolute(self, url):
        if not url:
            return None
        if url.startswith(('http://', 'https://')):
            return url
        if url.startswith('/') and not url.startswith('//'):
            return self.wasm_base_url() + url
        return None

    def wasm_page_meta(self, path, is_en=True, main_object=None, project=None, article=None, service=None, service_info=None):
        """Clean <title> and description for every ARFA page, computed in <head>.

        (Values set with t-set inside a page body are not visible to <head> in Odoo 19,
        which is why all pages showed "View name | website name" titles.)
        A title typed by an editor in "Optimize SEO" always wins: no title is returned then.
        """
        self.ensure_one()
        brand = (self.brand_name_en or 'ARFA Construction & Specialized Systems') if is_en \
            else (self.brand_name_ar or 'شركة عرفة للأنظمة المتخصصة')
        path = re.sub(r'^/[a-z]{2}(?:_[A-Za-z0-9]{2,4})?(?=/|$)', '', path or '/') or '/'
        if len(path) > 1:
            path = path.rstrip('/')
        name = desc = image = None
        # Only our own records, and only on their own page: list templates loop with
        # variables of the same name (t-as="project"), which would otherwise leak into <head>.
        if getattr(project, '_name', None) != 'wasm.project' or len(project) != 1 \
                or path != '/projects/%s' % project.id:
            project = None
        if getattr(article, '_name', None) != 'wasm.news' or len(article) != 1 \
                or path != '/news/%s' % article.id:
            article = None
        if getattr(service, '_name', None) != 'wasm.service' or len(service) != 1 \
                or path not in (service.website_url, '/services/%s' % service.slug):
            service = None
        if project:
            name = project.name
            bits = [project.name, project.location, project.scope_of_work or project.wasm_type_label(is_en)]
            desc = project.description or ' — '.join(b for b in bits if b)
            if project.image:
                image = self._wasm_absolute(project.wasm_main_image_url())
        elif article:
            name = (article.title_en or article.name) if is_en else (article.name or article.title_en)
            desc = (article.summary_en or article.summary) if is_en else (article.summary or article.summary_en)
            image = self._wasm_absolute(article.wasm_image_src())
        elif service:
            name = service.wasm_title()
            desc = service.intro or service.short_description
            if service.banner_image or service.image:
                image = self._wasm_absolute(service.wasm_banner_url())
        elif path in PAGE_IDS:
            Text = self.env['wasm.text'].sudo()
            lang = 'en_US' if is_en else 'ar_001'
            name = Text.get_text('seo.%s.title' % PAGE_IDS[path], lang) or None
            desc = Text.get_text('seo.%s.desc' % PAGE_IDS[path], lang) or None
        title = None
        user_title = hasattr(main_object, '_fields') and 'website_meta_title' in main_object._fields \
            and main_object.sudo()[:1].website_meta_title
        if name and not user_title:
            if path == '/':
                title = '%s | %s' % (brand, name)
            elif len(name) + len(brand) > 62:
                title = '%s | %s' % (name, 'ARFA' if is_en else 'عرفة')   # keep long project/news titles short
            else:
                title = '%s | %s' % (name, brand)
        desc = self._wasm_shorten(desc or self.wasm_site_description(is_en) or '')
        return {'title': title, 'name': name, 'description': desc, 'image': image}

    @api.model
    def wasm_patch_social_meta(self, website_meta, title, description, is_en, base_url, image=None):
        """Align Open Graph / Twitter tags with the page <title>, description and image.

        URLs are made absolute on ``web.base.url`` (``base_url`` from the request is only
        a fallback when that parameter is empty).
        """
        if not isinstance(website_meta, dict):
            return ''
        base = self.wasm_base_url(base_url)
        # hosts the visitor's request used (Odoo builds og:url / og:image from them)
        request_roots = {r.rstrip('/') for r in (base_url, request and request.httprequest.url_root) if r}

        def absolute(url):
            if not isinstance(url, str) or not url:
                return url
            if url.startswith('/') and not url.startswith('//'):
                return base + url
            for root in request_roots:
                if url == root or url.startswith(root + '/'):
                    return base + (url[len(root):] or '/')
            return url

        og = website_meta.get('opengraph_meta')
        tw = website_meta.get('twitter_meta')
        if isinstance(og, dict):
            if title:
                og['og:title'] = title
            if description:
                og['og:description'] = description
            og['og:locale'] = 'en_US' if is_en else 'ar_SA'
            if og.get('og:url'):
                og['og:url'] = absolute(og['og:url'])
            og['og:image'] = image or absolute(og.get('og:image'))
        if isinstance(tw, dict):
            if title:
                tw['twitter:title'] = title
            if description:
                tw['twitter:description'] = description
            tw['twitter:image'] = image or absolute(tw.get('twitter:image'))
        return ''

    def wasm_social_links(self):
        self.ensure_one()
        pairs = [('linkedin', self.social_linkedin), ('x', self.social_x), ('instagram', self.social_instagram),
                 ('facebook', self.social_facebook), ('youtube', self.social_youtube), ('tiktok', self.social_tiktok),
                 ('snapchat', self.social_snapchat)]
        links = {k: v.strip() for k, v in pairs if v and v.strip().startswith(('http://', 'https://'))}
        digits = self.wasm_phone_digits(self.contact_phone_secondary)
        if digits:
            links['whatsapp'] = 'https://wa.me/%s' % digits
        return links

    @staticmethod
    def _wasm_json_markup(data):
        """JSON for <script> tags: safe against '</script>' break-out."""
        text = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        text = text.replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
        return Markup(text)

    def wasm_social_json(self):
        self.ensure_one()
        return self._wasm_json_markup(self.wasm_social_links())

    def wasm_jsonld(self, base_url, page_title=None, page_path=None, is_en=True):
        """Schema.org graph: Organization/GeneralContractor + WebSite (+ BreadcrumbList on inner pages)."""
        self.ensure_one()
        base_url = self.wasm_base_url(base_url)
        name_en = self.brand_name_en or 'ARFA Construction & Specialized Systems'
        name_ar = self.brand_name_ar or 'شركة عرفة للأنظمة المتخصصة'
        services = self.env['wasm.service'].sudo().search([('active', '=', True)], order='sequence, id').mapped('name')
        org = {
            '@type': ['GeneralContractor', 'Organization'],
            '@id': base_url + '/#organization',
            'name': name_en if is_en else name_ar,
            'alternateName': [n for n in (name_ar if is_en else name_en, 'ARFA', 'ARFA SPECIALIZED SYSTEMS') if n],
            'url': base_url + '/',
            'logo': base_url + '/wasm_website/static/src/img/arfa_logo_stacked.png',
            'image': base_url + '/wasm_website/static/src/img/arfa_logo_horizontal.png',
            'description': self.wasm_site_description(is_en),
            'email': self.contact_email or None,
            'telephone': self.wasm_phone_e164(self.contact_phone) or None,
            'foundingDate': self.founding_year or None,
            'areaServed': {'@type': 'Country', 'name': self.service_area or 'Saudi Arabia'},
            'address': {
                '@type': 'PostalAddress',
                'streetAddress': one_line(self.wasm_t('contact_address', is_en)) or None,
                'addressCountry': 'SA',
            },
            'knowsAbout': [s for s in services if s],
            'makesOffer': [{'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': s}} for s in services if s],
            'sameAs': [v for k, v in self.wasm_social_links().items() if k != 'whatsapp'] or None,
        }
        if self.wasm_phone_digits(self.contact_phone_secondary):
            org['contactPoint'] = [{
                '@type': 'ContactPoint', 'contactType': 'sales',
                'telephone': self.wasm_phone_e164(self.contact_phone_secondary),
                'email': self.contact_email or None, 'areaServed': 'SA', 'availableLanguage': ['ar', 'en'],
            }]
        graph = [
            {k: v for k, v in org.items() if v not in (None, '', [], {})},
            {
                '@type': 'WebSite', '@id': base_url + '/#website', 'url': base_url + '/',
                'name': name_en if is_en else name_ar, 'inLanguage': 'en' if is_en else 'ar',
                'publisher': {'@id': base_url + '/#organization'},
            },
        ]
        if page_path and page_path not in ('/', '') and page_title:
            graph.append({
                '@type': 'BreadcrumbList',
                'itemListElement': [
                    {'@type': 'ListItem', 'position': 1, 'name': 'Home' if is_en else 'الرئيسية', 'item': base_url + '/'},
                    {'@type': 'ListItem', 'position': 2, 'name': page_title, 'item': base_url + page_path},
                ],
            })
        return self._wasm_json_markup({'@context': 'https://schema.org', '@graph': graph})

    def wasm_llms_text(self, base_url=None):
        """/llms.txt — a plain Markdown brief that AI assistants and AI search engines can quote."""
        self.ensure_one()
        env = self.env
        base_url = self.wasm_base_url(base_url)

        name = self.brand_name_en or 'ARFA Construction & Specialized Systems'
        out = ['# %s (%s)' % (name, self.brand_name_ar or ''), '',
               '> %s' % one_line(self.seo_description_en), '']
        facts = [('Founded', self.founding_year), ('Service area', self.service_area)]
        facts += [(item.title_en or item.title_ar, item.value) for item in self.items('stat')]
        facts += [('Phone', self.wasm_phone_e164(self.contact_phone)),
                  ('Mobile / WhatsApp', self.wasm_phone_e164(self.contact_phone_secondary)),
                  ('E-mail', self.contact_email), ('Address', self.contact_address_en),
                  ('Working hours', self.contact_working_hours_en)]
        out += ['## Key facts', ''] + ['- %s: %s' % (one_line(k), one_line(v)) for k, v in facts if k and v] + ['']
        out += ['## Services', '']
        for service in env['wasm.service'].sudo().with_context(lang='en_US').search([('active', '=', True)], order='sequence, id'):
            out.append('- [%s](%s%s): %s' % (one_line(service.name), base_url, service.website_url,
                                             one_line(service.short_description)))
        out += ['', '## Projects', '']
        for project in env['wasm.project'].sudo().with_context(lang='en_US').search(
                [('active', '=', True)], order='sequence, id desc', limit=50):
            bits = [one_line(b) for b in (project.location, project.client_name, project.scope_of_work) if b]
            out.append('- [%s](%s/projects/%s)%s' % (one_line(project.name), base_url, project.id,
                                                    (': ' + ' · '.join(bits)) if bits else ''))
        articles = env['wasm.news'].sudo().search([('active', '=', True)], order='date desc, id desc', limit=30)
        if articles:
            out += ['', '## News', '']
            for article in articles:
                title = one_line(article.title_en or article.name)
                summary = self._wasm_shorten(article.summary_en or article.summary or '', 200)
                out.append('- [%s](%s/news/%s) (%s)%s' % (title, base_url, article.id, article.date or '',
                                                         (': ' + summary) if summary else ''))
        out += ['', '## Main pages', '',
                '- [About](%s/about)' % base_url, '- [Services](%s/services)' % base_url,
                '- [Projects](%s/projects)' % base_url, '- [News](%s/news)' % base_url,
                '- [Request a quote](%s/quote)' % base_url, '- [Contact](%s/contactus)' % base_url,
                '- [Company profile (PDF)](%s/company-profile)' % base_url, '']
        social = self.wasm_social_links()
        if social:
            out += ['## Official channels', ''] + ['- %s: %s' % (k.capitalize(), v) for k, v in social.items()] + ['']
        return '\n'.join(out)
