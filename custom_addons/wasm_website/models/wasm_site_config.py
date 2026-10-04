# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

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
    'pillar1_img': '/wasm_website/static/src/img/pillar_civil.png',
    'pillar2_img': '/wasm_website/static/src/img/pillar_mep.png',
    'pillar3_img': '/wasm_website/static/src/img/pillar_mgmt.png',
    'why1_img': '/wasm_website/static/src/img/why_sbc.png',
    'why2_img': '/wasm_website/static/src/img/why_bim.png',
    'why3_img': '/wasm_website/static/src/img/why_machinery.png',
    'why4_img': '/wasm_website/static/src/img/why_timelines.png',
    'why5_img': '/wasm_website/static/src/img/why_qc.png',
    'why6_img': '/wasm_website/static/src/img/why_safety.png',
    'srv1_img': '/wasm_website/static/src/img/arfa_exhibition_building.webp',
    'srv2_img': '/wasm_website/static/src/img/arfa_electrical_panels.webp',
    'srv3_img': '/wasm_website/static/src/img/service_card_3.jpg',
    'srv4_img': '/wasm_website/static/src/img/service_card_4.jpg',
    'srv5_img': '/wasm_website/static/src/img/service_card_5.jpg',
    'srv6_img': '/wasm_website/static/src/img/service_card_6.jpg',
    'srv7_img': '/wasm_website/static/src/img/service_card_7.jpg',
    'srv8_img': '/wasm_website/static/src/img/service_card_8.jpg',
    'hero_bg_image': '/wasm_website/static/src/img/hero_bg.png',
    'showcase_poster': '',
    'showcase_bg_image': '',
}


def _ar(name):
    return AR_DEFAULTS.get(name, '')


class WasmSiteConfig(models.Model):
    _name = 'wasm.site.config'
    _description = 'Site Config & Media Settings - ARFA SPECIALIZED SYSTEMS'

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

    # Pillar Cards (3 Hero Cards)
    pillar1_img = fields.Image(string='Pillar 1 Image', max_width=1200, max_height=800)
    pillar1_title_ar = fields.Char(string='Pillar 1 Title (Arabic)', default=_ar('pillar1_title_ar'))
    pillar1_title_en = fields.Char(string='Pillar 1 Title (English)', default='Structural & Civil Contracting')
    pillar1_desc_ar = fields.Text(string='Pillar 1 Description (Arabic)', default=_ar('pillar1_desc_ar'))
    pillar1_desc_en = fields.Text(string='Pillar 1 Description (English)', default='Concrete framing, foundations, and heavy structural developments executed strictly to SBC codes.')
    pillar1_link = fields.Char(string='Pillar 1 URL', default='/services')

    pillar2_img = fields.Image(string='Pillar 2 Image', max_width=1200, max_height=800)
    pillar2_title_ar = fields.Char(string='Pillar 2 Title (Arabic)', default=_ar('pillar2_title_ar'))
    pillar2_title_en = fields.Char(string='Pillar 2 Title (English)', default='MEP & Mechanical Systems')
    pillar2_desc_ar = fields.Text(string='Pillar 2 Description (Arabic)', default=_ar('pillar2_desc_ar'))
    pillar2_desc_en = fields.Text(string='Pillar 2 Description (English)', default='Advanced HVAC ducting, plumbing, electrical grid infrastructure, and smart automation.')
    pillar2_link = fields.Char(string='Pillar 2 URL', default='/services')

    pillar3_img = fields.Image(string='Pillar 3 Image', max_width=1200, max_height=800)
    pillar3_title_ar = fields.Char(string='Pillar 3 Title (Arabic)', default=_ar('pillar3_title_ar'))
    pillar3_title_en = fields.Char(string='Pillar 3 Title (English)', default='Turnkey Project Delivery')
    pillar3_desc_ar = fields.Text(string='Pillar 3 Description (Arabic)', default=_ar('pillar3_desc_ar'))
    pillar3_desc_en = fields.Text(string='Pillar 3 Description (English)', default='Comprehensive engineering management, interior fitouts, and end-to-end turnkey delivery.')
    pillar3_link = fields.Char(string='Pillar 3 URL', default='/services')

    # Company Statistics (4 Cards)
    stat1_val = fields.Char(string='Stat 1 Value', default='150+')
    stat1_label_ar = fields.Char(string='Stat 1 Label (Arabic)', default=_ar('stat1_label_ar'))
    stat1_label_en = fields.Char(string='Stat 1 Label (English)', default='Completed Projects')

    stat2_val = fields.Char(string='Stat 2 Value', default='18+')
    stat2_label_ar = fields.Char(string='Stat 2 Label (Arabic)', default=_ar('stat2_label_ar'))
    stat2_label_en = fields.Char(string='Stat 2 Label (English)', default='Years Experience')

    stat3_val = fields.Char(string='Stat 3 Value', default='1,200,000+')
    stat3_label_ar = fields.Char(string='Stat 3 Label (Arabic)', default=_ar('stat3_label_ar'))
    stat3_label_en = fields.Char(string='Stat 3 Label (English)', default='m² Executed Area')

    stat4_val = fields.Char(string='Stat 4 Value', default='85+')
    stat4_label_ar = fields.Char(string='Stat 4 Label (Arabic)', default=_ar('stat4_label_ar'))
    stat4_label_en = fields.Char(string='Stat 4 Label (English)', default='Engineers & Specialists')

    # Why Choose Us Cards (6 Cards)
    why1_img = fields.Image(string='Why 1 Image', max_width=1200, max_height=800)
    why1_title_ar = fields.Char(string='Why 1 Title (Arabic)', default=_ar('why1_title_ar'))
    why1_title_en = fields.Char(string='Why 1 Title (English)', default='SBC Code Compliance')
    why1_desc_ar = fields.Text(string='Why 1 Description (Arabic)', default=_ar('why1_desc_ar'))
    why1_desc_en = fields.Text(string='Why 1 Description (English)', default='Strict adherence to Saudi Building Code specifications across all concrete structural works.')

    why2_img = fields.Image(string='Why 2 Image', max_width=1200, max_height=800)
    why2_title_ar = fields.Char(string='Why 2 Title (Arabic)', default=_ar('why2_title_ar'))
    why2_title_en = fields.Char(string='Why 2 Title (English)', default='BIM 3D Project Tech')
    why2_desc_ar = fields.Text(string='Why 2 Description (Arabic)', default=_ar('why2_desc_ar'))
    why2_desc_en = fields.Text(string='Why 2 Description (English)', default='Advanced 3D modeling and clash detection prior to site execution ensuring zero errors.')

    why3_img = fields.Image(string='Why 3 Image', max_width=1200, max_height=800)
    why3_title_ar = fields.Char(string='Why 3 Title (Arabic)', default=_ar('why3_title_ar'))
    why3_title_en = fields.Char(string='Why 3 Title (English)', default='Owned Heavy Machinery')
    why3_desc_ar = fields.Text(string='Why 3 Description (Arabic)', default=_ar('why3_desc_ar'))
    why3_desc_en = fields.Text(string='Why 3 Description (English)', default='Complete fleet of excavators, cranes, and concrete pumps to accelerate timelines.')

    why4_img = fields.Image(string='Why 4 Image', max_width=1200, max_height=800)
    why4_title_ar = fields.Char(string='Why 4 Title (Arabic)', default=_ar('why4_title_ar'))
    why4_title_en = fields.Char(string='Why 4 Title (English)', default='Strict Timelines')
    why4_desc_ar = fields.Text(string='Why 4 Description (Arabic)', default=_ar('why4_desc_ar'))
    why4_desc_en = fields.Text(string='Why 4 Description (English)', default='Guaranteed project completion within agreed schedule and transparent budget.')

    why5_img = fields.Image(string='Why 5 Image', max_width=1200, max_height=800)
    why5_title_ar = fields.Char(string='Why 5 Title (Arabic)', default=_ar('why5_title_ar'))
    why5_title_en = fields.Char(string='Why 5 Title (English)', default='Certified Quality Lab')
    why5_desc_ar = fields.Text(string='Why 5 Description (Arabic)', default=_ar('why5_desc_ar'))
    why5_desc_en = fields.Text(string='Why 5 Description (English)', default='Rigorous core testing and ultrasound concrete strength inspection on site.')

    why6_img = fields.Image(string='Why 6 Image', max_width=1200, max_height=800)
    why6_title_ar = fields.Char(string='Why 6 Title (Arabic)', default=_ar('why6_title_ar'))
    why6_title_en = fields.Char(string='Why 6 Title (English)', default='ISO & Site Safety Compliance')
    why6_desc_ar = fields.Text(string='Why 6 Description (Arabic)', default=_ar('why6_desc_ar'))
    why6_desc_en = fields.Text(string='Why 6 Description (English)', default='Zero-hazard workplace policies adhering to international safety frameworks.')

    # Service Cards (8 Cards matching exact website menu tabs)
    srv1_img = fields.Image(string='Service 1 Image', max_width=1200, max_height=800)
    srv1_title_ar = fields.Char(string='Service 1 Title (Arabic)', default=_ar('srv1_title_ar'))
    srv1_title_en = fields.Char(string='Service 1 Title (English)', default='Modern building systems')
    srv1_desc_ar = fields.Text(string='Service 1 Description (Arabic)', default=_ar('srv1_desc_ar'))
    srv1_desc_en = fields.Text(string='Service 1 Description (English)', default='Advanced modern construction tech, glass facades, prefab steel framing, and turnkey fitouts.')
    srv1_url = fields.Char(string='Service 1 URL', default='/modern-building-systems')

    srv2_img = fields.Image(string='Service 2 Image', max_width=1200, max_height=800)
    srv2_title_ar = fields.Char(string='Service 2 Title (Arabic)', default=_ar('srv2_title_ar'))
    srv2_title_en = fields.Char(string='Service 2 Title (English)', default='Electromechanical systems')
    srv2_desc_ar = fields.Text(string='Service 2 Description (Arabic)', default=_ar('srv2_desc_ar'))
    srv2_desc_en = fields.Text(string='Service 2 Description (English)', default='Design, supply, and installation of power grids, mechanical infrastructure, and sanitary networks.')
    srv2_url = fields.Char(string='Service 2 URL', default='/electromechanical-systems')

    srv3_img = fields.Image(string='Service 3 Image', max_width=1200, max_height=800)
    srv3_title_ar = fields.Char(string='Service 3 Title (Arabic)', default=_ar('srv3_title_ar'))
    srv3_title_en = fields.Char(string='Service 3 Title (English)', default='Smart building systems')
    srv3_desc_ar = fields.Text(string='Service 3 Description (Arabic)', default=_ar('srv3_desc_ar'))
    srv3_desc_en = fields.Text(string='Service 3 Description (English)', default='Building automation, smart control panels, security systems, and early warning technology.')
    srv3_url = fields.Char(string='Service 3 URL', default='/smart-building-systems')

    srv4_img = fields.Image(string='Service 4 Image', max_width=1200, max_height=800)
    srv4_title_ar = fields.Char(string='Service 4 Title (Arabic)', default=_ar('srv4_title_ar'))
    srv4_title_en = fields.Char(string='Service 4 Title (English)', default='Alternative energy solutions')
    srv4_desc_ar = fields.Text(string='Service 4 Description (Arabic)', default=_ar('srv4_desc_ar'))
    srv4_desc_en = fields.Text(string='Service 4 Description (English)', default='Photovoltaic solar energy systems and energy optimization solutions for commercial sectors.')
    srv4_url = fields.Char(string='Service 4 URL', default='/alternative-energy-solutions')

    srv5_img = fields.Image(string='Service 5 Image', max_width=1200, max_height=800)
    srv5_title_ar = fields.Char(string='Service 5 Title (Arabic)', default=_ar('srv5_title_ar'))
    srv5_title_en = fields.Char(string='Service 5 Title (English)', default='Fire protection & prevention systems')
    srv5_desc_ar = fields.Text(string='Service 5 Description (Arabic)', default=_ar('srv5_desc_ar'))
    srv5_desc_en = fields.Text(string='Service 5 Description (English)', default='Automatic fire suppression, alarm networks, and civil defense certified pump installations.')
    srv5_url = fields.Char(string='Service 5 URL', default='/fire-protection-prevention-systems')

    srv6_img = fields.Image(string='Service 6 Image', max_width=1200, max_height=800)
    srv6_title_ar = fields.Char(string='Service 6 Title (Arabic)', default=_ar('srv6_title_ar'))
    srv6_title_en = fields.Char(string='Service 6 Title (English)', default='Medical Gas Systems')
    srv6_desc_ar = fields.Text(string='Service 6 Description (Arabic)', default=_ar('srv6_desc_ar'))
    srv6_desc_en = fields.Text(string='Service 6 Description (English)', default='Design and installation of central medical gas pipelines and operating theatre infrastructure.')
    srv6_url = fields.Char(string='Service 6 URL', default='/medical-gas-systems')

    srv7_img = fields.Image(string='Service 7 Image', max_width=1200, max_height=800)
    srv7_title_ar = fields.Char(string='Service 7 Title (Arabic)', default=_ar('srv7_title_ar'))
    srv7_title_en = fields.Char(string='Service 7 Title (English)', default='Infrastructure Development')
    srv7_desc_ar = fields.Text(string='Service 7 Description (Arabic)', default=_ar('srv7_desc_ar'))
    srv7_desc_en = fields.Text(string='Service 7 Description (English)', default='Underground piping, drainage networks, site excavation, and public infrastructure works.')
    srv7_url = fields.Char(string='Service 7 URL', default='/infrastructure-development')

    srv8_img = fields.Image(string='Service 8 Image', max_width=1200, max_height=800)
    srv8_title_ar = fields.Char(string='Service 8 Title (Arabic)', default=_ar('srv8_title_ar'))
    srv8_title_en = fields.Char(string='Service 8 Title (English)', default='Planning & Construction')
    srv8_desc_ar = fields.Text(string='Service 8 Description (Arabic)', default=_ar('srv8_desc_ar'))
    srv8_desc_en = fields.Text(string='Service 8 Description (English)', default='Concrete framing, foundations, and heavy structural developments executed strictly to SBC code.')
    srv8_url = fields.Char(string='Service 8 URL', default='/planning-construction')

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
