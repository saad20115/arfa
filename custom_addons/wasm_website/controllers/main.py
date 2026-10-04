# -*- coding: utf-8 -*-
import base64
import logging
import os
from odoo import http, _
from odoo.http import request

from odoo.addons.wasm_website.models.wasm_site_config import DEFAULT_IMAGES

_logger = logging.getLogger(__name__)

ALLOWED_CUSTOMER_TYPES = ('individual', 'company', 'government')
ALLOWED_PROJECT_TYPES = ('commercial', 'residential', 'industrial', 'infrastructure', 'renovation')
ALLOWED_DEPARTMENTS = ('engineering', 'sales', 'projects', 'hr', 'management')

# --- File Upload Security Constants ---
ALLOWED_FILE_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv',
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
    '.dwg', '.dxf', '.zip', '.rar',
}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB per file
MAX_FILES_COUNT = 5  # Maximum number of files per submission


class WasmWebsiteController(http.Controller):

    @http.route('/', type='http', auth='public', website=True)
    def wasm_home(self, **kw):
        site_config = request.env['wasm.site.config'].sudo().get_config()
        home_limit = site_config.home_projects_limit if site_config and site_config.home_projects_limit > 0 else 6
        services = request.env['wasm.service'].sudo().search(
            [('active', '=', True)], limit=6, order='sequence, id'
        )
        projects = request.env['wasm.project'].sudo().search(
            [('active', '=', True)], limit=home_limit, order='sequence, id desc'
        )
        partners = request.env['wasm.partner'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        testimonials = request.env['wasm.testimonial'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        values = {
            'services': services,
            'projects': projects,
            'partners': partners,
            'testimonials': testimonials,
            'site_config': site_config,
            'stats': {
                'stat1_val': site_config.stat1_val if site_config and site_config.stat1_val else '150+',
                'stat1_label_ar': site_config.stat1_label_ar if site_config and site_config.stat1_label_ar else 'مشروع مكتمل',
                'stat1_label_en': site_config.stat1_label_en if site_config and site_config.stat1_label_en else 'Completed Projects',

                'stat2_val': site_config.stat2_val if site_config and site_config.stat2_val else '18+',
                'stat2_label_ar': site_config.stat2_label_ar if site_config and site_config.stat2_label_ar else 'عاماً خبرة',
                'stat2_label_en': site_config.stat2_label_en if site_config and site_config.stat2_label_en else 'Years Experience',

                'stat3_val': site_config.stat3_val if site_config and site_config.stat3_val else '1,200,000+',
                'stat3_label_ar': site_config.stat3_label_ar if site_config and site_config.stat3_label_ar else 'م² مساحة منفذة',
                'stat3_label_en': site_config.stat3_label_en if site_config and site_config.stat3_label_en else 'm² Executed Area',

                'stat4_val': site_config.stat4_val if site_config and site_config.stat4_val else '85+',
                'stat4_label_ar': site_config.stat4_label_ar if site_config and site_config.stat4_label_ar else 'مهندس ومتخصص',
                'stat4_label_en': site_config.stat4_label_en if site_config and site_config.stat4_label_en else 'Engineers & Specialists',
            }
        }
        return request.render('wasm_website.home_page_template', values)

    # ------------------------------------------------------------------
    # Binary streaming helper
    # ------------------------------------------------------------------
    def _wasm_stream(self, record, field_name, fallback_url=None, mimetype=None,
                     filename=None, default_mimetype='image/png', as_attachment=False):
        """Stream a binary/image field efficiently.

        Uses Odoo's ir.binary streaming: the file is served straight from the
        filestore (no base64 decode of the whole file in Python), with the right
        mimetype, ETag / 304 support and HTTP Range support (needed for video).
        When the request carries ?unique=..., the response is cached by the
        browser for a year (the templates change the token on every save).
        """
        if record and record.exists() and record[field_name]:
            unique = bool(request.params.get('unique'))
            try:
                binary = request.env['ir.binary']
                if default_mimetype.startswith('image/') and not mimetype:
                    stream = binary._get_image_stream_from(record, field_name, filename=filename)
                else:
                    stream = binary._get_stream_from(record, field_name, filename=filename,
                                                     mimetype=mimetype, default_mimetype=default_mimetype)
                return stream.get_response(as_attachment=as_attachment, immutable=unique)
            except Exception:  # safety net: keep the page working even if the API changes
                _logger.exception('wasm_website: streaming %s.%s failed, using fallback', record._name, field_name)
                data = base64.b64decode(record[field_name])
                return request.make_response(data, headers=[
                    ('Content-Type', mimetype or default_mimetype),
                    ('Content-Length', str(len(data))),
                    ('Cache-Control', 'public, max-age=31536000, immutable' if unique else 'no-cache'),
                ])
        if fallback_url:
            return request.redirect(fallback_url, local=fallback_url.startswith('/'))
        return request.not_found()

    @http.route('/wasm/config/image/<string:field_name>', type='http', auth='public')
    def wasm_config_image(self, field_name, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        field = config._fields.get(field_name)
        if not field or field.type != 'binary' or field_name not in DEFAULT_IMAGES:
            return request.not_found()
        return self._wasm_stream(config, field_name, fallback_url=DEFAULT_IMAGES.get(field_name) or None)

    @http.route('/wasm/partner/<int:partner_id>/logo', type='http', auth='public')
    def wasm_partner_logo_stream(self, partner_id, **kw):
        partner = request.env['wasm.partner'].sudo().browse(partner_id)
        if partner.exists() and not partner.logo and partner.logo_url:
            return request.redirect(partner.logo_url, local=False)
        return self._wasm_stream(partner, 'logo')

    @http.route('/wasm/project/<int:project_id>/image', type='http', auth='public')
    def wasm_project_image_stream(self, project_id, **kw):
        project = request.env['wasm.project'].sudo().browse(project_id)
        defaults = {
            47: '/wasm_website/static/src/img/project_conference_ritz.jpg',
            48: '/wasm_website/static/src/img/project_qirwan_kitchen.jpg',
            49: '/wasm_website/static/src/img/project_sudair_industrial.jpg',
            50: '/wasm_website/static/src/img/project_intercontinental_taif.jpg',
            51: '/wasm_website/static/src/img/project_mina_hospital.jpg',
            52: '/wasm_website/static/src/img/project_janadriyah_towers.jpg',
            53: '/wasm_website/static/src/img/project_sofitel_makkah.jpg',
            54: '/wasm_website/static/src/img/project_ramada_meridien.jpg',
        }
        return self._wasm_stream(project, 'image',
                                 fallback_url=defaults.get(project_id, '/wasm_website/static/src/img/project_conference_ritz.jpg'))

    @http.route('/wasm/pillar/<int:pillar_num>/image', type='http', auth='public')
    def wasm_pillar_image_stream(self, pillar_num, **kw):
        """Kept for old links; templates now use site_config.wasm_img_url()."""
        return self.wasm_config_image('pillar%d_img' % pillar_num)

    @http.route('/wasm/why/<int:card_num>/image', type='http', auth='public')
    def wasm_why_card_image_stream(self, card_num, **kw):
        """Kept for old links; templates now use site_config.wasm_img_url()."""
        return self.wasm_config_image('why%d_img' % card_num)

    @http.route(['/wasm/service_card/<int:card_num>/image', '/wasm/service/<int:service_id>/image'], type='http', auth='public')
    def wasm_service_card_image_stream(self, card_num=None, service_id=None, **kw):
        if service_id:
            service = request.env['wasm.service'].sudo().browse(service_id)
            return self._wasm_stream(service, 'image',
                                     fallback_url='/wasm_website/static/src/img/arfa_exhibition_building.webp')
        return self.wasm_config_image('srv%d_img' % (card_num or 1))

    # --- Service Subpage Routes matching website navigation tabs ---
    @http.route([
        '/planning-construction',
        '/electromechanical-systems',
        '/smart-building-systems',
        '/modern-building-systems',
        '/fire-protection-prevention-systems',
        '/medical-gas-systems',
        '/alternative-energy-solutions',
        '/infrastructure-development'
    ], type='http', auth='public', website=True)
    def wasm_service_tab_page(self, **kw):
        path = request.httprequest.path
        services_data = {
            '/planning-construction': {
                'id': 1,
                'card_num': 1,
                'title_en': 'Planning & Structural Construction',
                'title_ar': 'التخطيط والإنشاءات الخرسانية',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS offers full-scale engineering management, structural design, and general contracting services for complex residential, commercial, industrial, and healthcare developments.',
                'subtitle_ar': 'تقدم شركة عرفة للأنظمة المتخصصة إدارة هندسية وتصميم إنشائي ومقاولات عامة للمشاريع السكنية والتجارية والصناعية والصحية.',
                'icon': 'fa-building',
                'bg_img': '/wasm_website/static/src/img/official_live_services/planning-construction_img_1.webp',
                'badge_en': 'Structural Design & General Contracting',
                'badge_ar': 'التصميم الإنشائي والمقاولات العامة',
                'features_en': [
                    'Full-scale engineering management & structural design for complex developments.',
                    'General contracting across residential, commercial, industrial, & healthcare sectors.',
                    'Value engineering, strict quality control, and schedule management.',
                    'Resilient, modern structures built to the highest Saudi Building Code (SBC) standards.'
                ],
                'features_ar': [
                    'إدارة هندسية وتصميم إنشائي متكامل للمشاريع المعقدة.',
                    'تنفيذ الأعمال الإنشائية والمقاولات العامة لكافة القطاعات.',
                    'الهندسة القيمية والرقابة الصارمة على الجودة والجداول الزمنية.',
                    'مبانٍ وبنى حديثة ومقاومة وفق أعلى معايير كود البناء السعودي SBC.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/planning-construction_img_6.webp'
                ]
            },
            '/electromechanical-systems': {
                'id': 2,
                'card_num': 2,
                'title_en': 'Electromechanical Systems (MEP)',
                'title_ar': 'أنظمة الكهروميكانيك (MEP)',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS boasts a highly qualified engineering and technical team specializing in the design, execution, and maintenance of complete MEP infrastructure.',
                'subtitle_ar': 'تتميز شركة عرفة للأنظمة المتخصصة بكادر هندسي وفني عالي التأهيل متخصص في تصميم وتنفيذ وصيانة شبكات الكهروميكانيك.',
                'icon': 'fa-bolt',
                'bg_img': '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_1.webp',
                'badge_en': 'Complete MEP Engineering',
                'badge_ar': 'حلول الكهروميكانيك المتقدمة',
                'features_en': [
                    'Central air conditioning, cooling plants, and precision ductwork systems.',
                    'Plumbing infrastructure, drainage networks, and swimming pool construction.',
                    'Firefighting, FM-200 / CO2 gas fire suppression, and alarm systems.',
                    'BMS Systems, electrical distribution, power transformers, and low-voltage networks.'
                ],
                'features_ar': [
                    'أنظمة التكييف المركزي ومحطات التبريد وإمدادات الدكت.',
                    'شبكات السباكة وتصريف المياه وإنشاء حمامات السباحة.',
                    'أنظمة إطفاء الحريق والإغمار بالغاز وشبكات الإنذار المبكر.',
                    'أنظمة BMS والتحكم الكهربائي ومحطات الجهد المنخفض.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/electromechanical-systems_img_6.webp'
                ]
            },
            '/smart-building-systems': {
                'id': 3,
                'card_num': 3,
                'title_en': 'Smart Building Systems (BMS)',
                'title_ar': 'أنظمة المباني الذكية (BMS)',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS implements smart building solutions across residential and commercial developments, enabling clients to effortlessly control and manage all integrated systems remotely.',
                'subtitle_ar': 'تطبق شركة عرفة للأنظمة المتخصصة حلول المباني الذكية في المشاريع السكنية والتجارية لتمكين التحكم والتعديل عن بُعد.',
                'icon': 'fa-microchip',
                'bg_img': '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_1.webp',
                'badge_en': 'Building Automation & Remote Control',
                'badge_ar': 'أتمتة المباني والتحكم الرقمي',
                'features_en': [
                    'Integrated BMS for centralized energy, climate, and smart lighting control.',
                    'Remote management of facility operations with minimal human intervention.',
                    'IP CCTV surveillance integration and biometric access control systems.',
                    'Real-time automated diagnostic monitoring and predictive maintenance sensors.'
                ],
                'features_ar': [
                    'أنظمة BMS المركزية لإدارة الطاقة والإضاءة والتكييف الذكي.',
                    'التحكم والتعديل عن بُعد بالمنشآت مع تقليل التدخل البشرى.',
                    'ربط أنظمة المراقبة الرقمية CCTV وبوابات الدخول المغناطيسية.',
                    'مراقبة تشخيصية فورية للتنبيه بالأعطال والصيانة التنبؤية.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/smart-building-systems_img_6.webp'
                ]
            },
            '/modern-building-systems': {
                'id': 4,
                'card_num': 4,
                'title_en': 'Modern Building Systems & Prefab',
                'title_ar': 'الأنظمة الحديثة والمباني (Prefab)',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS is one of the leading companies to adopt modern building systems across all construction departments, reducing overall costs and maximizing resource efficiency.',
                'subtitle_ar': 'تعتبر شركة عرفة للأنظمة المتخصصة من الشركات الرائدة في تبني أنظمة البناء الحديثة لتقليل التكاليف وزيادة الكفاءة.',
                'icon': 'fa-cubes',
                'bg_img': '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_1.webp',
                'badge_en': 'Fast & Sustainable Construction Tech',
                'badge_ar': 'تقنيات البناء الحديثة والمستدامة',
                'features_en': [
                    'Adoption of advanced modern building systems across all construction sectors.',
                    'Maximized efficiency of modern building resources reducing total development costs.',
                    'Structural glass facades, curtain walls, and premium aluminum cladding.',
                    'Prefabricated modular building methods with superior thermal insulation.'
                ],
                'features_ar': [
                    'تبني أحدث تقنيات وأنظمة البناء الحديثة بكافة قطاعات التشييد.',
                    'تعظيم كفاءة الموارد الحديثة وتقليل التكلفة الإجمالية للمشاريع.',
                    'تركيب الواجهات الزجاجية والهياكل المعدنية والألومنيوم الفاخر.',
                    'أنظمة البناء مسبق الصنع المودولار بأعلى مستويات العزل الحراري.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/modern-building-systems_img_6.webp'
                ]
            },
            '/fire-protection-prevention-systems': {
                'id': 5,
                'card_num': 5,
                'title_en': 'Fire Protection & Prevention Systems',
                'title_ar': 'أنظمة الوقاية والحماية من الحريق',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS designs, installs, and maintains high-performance fire protection and prevention systems adhering strictly to Civil Defense regulations and NFPA, UL, and FM standards.',
                'subtitle_ar': 'تصمم وتنفذ وتصين شركة عرفة للأنظمة المتخصصة أنظمة السلامة والوقاية من الحريق المعتمدة من الدفاع المدني والمعايير الدولية (NFPA, UL, FM).',
                'icon': 'fa-fire-extinguisher',
                'bg_img': '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_1.webp',
                'badge_en': 'Civil Defense & NFPA Certified Safety',
                'badge_ar': 'معتمدة من الدفاع المدني وNFPA',
                'features_en': [
                    'Smart addressable fire alarm, smoke detection, and aspirating early-warning networks.',
                    'Automatic sprinkler networks, deluge systems, and UL/FM fire pump stations.',
                    'Clean agent gas suppression (FM-200, CO2, Novec 1230) for server rooms and data centers.',
                    'Testing, commissioning, and official Saudi Civil Defense licensing certification.'
                ],
                'features_ar': [
                    'شبكات إنذار كشف الدخان والتنبيه المبكر المعنونة.',
                    'شبكات الرش الآلي ومحطات مضخات الحريق المعيارية UL/FM.',
                    'أنظمة الإطفاء التلقائي بالغازات النظيفة لغرف البيانات والمعدات.',
                    'اختبارات التشغيل واختبار الضغط وتراخيص الدفاع المدني المعتمدة.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/fire-protection-prevention-systems_img_6.webp'
                ]
            },
            '/medical-gas-systems': {
                'id': 6,
                'card_num': 6,
                'title_en': 'Medical Gas Systems (MGPS)',
                'title_ar': 'أنظمة الغازات الطبية (MGPS)',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS provides end-to-end engineering solutions for Medical Gas Pipeline Systems (MGPS) in healthcare facilities according to strict HTM 02-01 / NFPA 99 standards.',
                'subtitle_ar': 'تقدم شركة عرفة للأنظمة المتخصصة حلولاً هندسية متكاملة لشبكات الغازات الطبية بالمنشآت الصحية وفق معايير HTM 02-01 وNFPA 99.',
                'icon': 'fa-medkit',
                'bg_img': '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_1.webp',
                'badge_en': 'HTM 02-01 / NFPA 99 Hospital Standards',
                'badge_ar': 'معايير المستشفيات العالمية HTM/NFPA',
                'features_en': [
                    'Medical Gas Pipeline Systems (MGPS) for hospitals and specialized medical centers.',
                    'Central oxygen supply stations, surgical air, and high-vacuum plant installations.',
                    'Bedhead units (BHU), ICU monitoring panels, and digital gas pressure alarms.',
                    'Full testing and clinical safety compliance to HTM 02-01 and NFPA 99 code.'
                ],
                'features_ar': [
                    'شبكات تمديد الغازات الطبية المركزية للمستشفيات والجهات الصحية.',
                    'محطات الأكسجين المركزية وضواغط الهواء والمطارد الجراحية.',
                    'وحدات رؤوس الأسرة (BHU) ولوحات المراقبة الرقمية لغرف العناية.',
                    'اختبارات النقاء والضغط والاعتماد الطبي وفق HTM 02-01 وNFPA 99.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/medical-gas-systems_img_6.webp'
                ]
            },
            '/alternative-energy-solutions': {
                'id': 7,
                'card_num': 7,
                'title_en': 'Alternative Energy Solutions',
                'title_ar': 'حلول الطاقة البديلة والشمسية',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS implements sustainable renewable and alternative energy solutions designed to optimize power consumption, reduce carbon footprint, and protect the environment.',
                'subtitle_ar': 'تطبق شركة عرفة للأنظمة المتخصصة حلول الطاقة التجددية والبديلة المستدامة لترشيد استهلاك الكهرباء وتقليل الأثر الكربونى.',
                'icon': 'fa-sun-o',
                'bg_img': '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_1.webp',
                'badge_en': 'Solar PV & Sustainable Energy',
                'badge_ar': 'الطاقة الشمسية والاستدامة البيئية',
                'features_en': [
                    'Rooftop and ground-mounted commercial solar PV system design and installation.',
                    'Smart power consumption optimization reducing electrical utility expenditure.',
                    'Carbon footprint reduction and environmentally friendly infrastructure.',
                    'Grid-tied inverters and high-capacity battery energy storage setups (BESS).'
                ],
                'features_ar': [
                    'تصميم وتثبيت أنظمة الألواح الشمسية الكهروضوئية للمشروعات والمباني.',
                    'ترشيد استهلاك الكهرباء وخفض التكاليف التشغيلية للفواتير.',
                    'تقليل الانبعاثات الكربونية وحماية البيئة وفق معايير الاستدامة.',
                    'محولات الطاقة الهجينة وأنظمة بطاريات التخزين المستمرة.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/alternative-energy-solutions_img_6.webp'
                ]
            },
            '/infrastructure-development': {
                'id': 8,
                'card_num': 8,
                'title_en': 'Infrastructure Development & Networks',
                'title_ar': 'البنية التحتية والشبكات',
                'subtitle_en': 'ARFA SPECIALIZED SYSTEMS delivers comprehensive infrastructure engineering solutions for wet and dry utility networks, power distribution, district cooling, and stormwater management.',
                'subtitle_ar': 'تقدم شركة عرفة للأنظمة المتخصصة حلول هندسية متكاملة لشبكات البنية التحتية الجافة والمائية وتوزيع الكهرباء وتصريف السيول.',
                'icon': 'fa-road',
                'bg_img': '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_1.webp',
                'badge_en': 'Heavy Utilities & Infrastructure Networks',
                'badge_ar': 'شبكات البنية التحتية الكبرى',
                'features_en': [
                    'Constructing robust wet and dry utility networks for residential & commercial plots.',
                    'High-capacity electrical power distribution lines and district cooling pipelines.',
                    'Stormwater management, drainage networks, and site excavation & grading.',
                    'Advanced underground telecommunication pathways built for future expansion.'
                ],
                'features_ar': [
                    'إنشاء شبكات المرافق الجافة والمائية للمخططات السكنية والتجارية.',
                    'خطوط توزيع الكهرباء عالية السعة وأنابيب التبريد المركزي.',
                    'تصريف السيول ومياه الأمطار وأعمال الحفر وتسوية المواقع.',
                    'مسارات الاتصالات الأرضية وغرف التفتيش الجاهزة للتوسع المستقبلي.'
                ],
                'gallery_imgs': [
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_1.webp',
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_2.webp',
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_3.webp',
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_4.webp',
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_5.webp',
                    '/wasm_website/static/src/img/official_live_services/infrastructure-development_img_6.webp'
                ]
            }
        }

        info = services_data.get(path, services_data['/planning-construction'])
        site_config = request.env['wasm.site.config'].sudo().get_config()
        values = {
            'service_info': info,
            'site_config': site_config,
            'all_services_data': services_data,
        }
        return request.render('wasm_website.service_tab_detail_template', values)

    @http.route('/wasm/video/showcase', type='http', auth='public')
    def wasm_showcase_video_stream(self, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        fallback = config.showcase_video_url or '/wasm_website/static/src/video/hero_construction.mp4'
        return self._wasm_stream(config, 'showcase_video_file', fallback_url=fallback,
                                 mimetype='video/mp4', default_mimetype='video/mp4',
                                 filename=config.showcase_video_filename or 'showcase.mp4')

    @http.route('/wasm/video/poster', type='http', auth='public')
    def wasm_showcase_poster_stream(self, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        return self._wasm_stream(config, 'showcase_poster')

    @http.route('/wasm/video/bg', type='http', auth='public')
    def wasm_showcase_bg_stream(self, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        return self._wasm_stream(config, 'showcase_bg_image')

    @http.route(['/about', '/about-us'], type='http', auth='public', website=True)
    def wasm_about(self, **kw):
        return request.render('wasm_website.about_page_template', {})

    @http.route(['/our-company', '/our-group', '/group-companies'], type='http', auth='public', website=True)
    def wasm_our_company(self, **kw):
        site_config = request.env['wasm.site.config'].sudo().get_config()
        values = {
            'site_config': site_config,
        }
        return request.render('wasm_website.our_company_page_template', values)

    @http.route(['/company-profile', '/company-profile.pdf', '/download/company-profile'], type='http', auth='public', website=True, sitemap=False)
    def wasm_company_profile_download(self, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        if config.company_profile_pdf:
            return self._wasm_stream(config, 'company_profile_pdf', mimetype='application/pdf',
                                     default_mimetype='application/pdf',
                                     filename=config.company_profile_filename or 'Arfa_Company_Profile_2026.pdf')
        # Bundled file: served by the static file handler (streamed, cached, range requests).
        return request.redirect('/wasm_website/static/src/pdf/arfa_company_profile.pdf')

    @http.route(['/services', '/our-services'], type='http', auth='public', website=True)
    def wasm_services(self, **kw):
        services = request.env['wasm.service'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        return request.render('wasm_website.services_page_template', {'services': services})

    @http.route(['/projects', '/our-projects'], type='http', auth='public', website=True)
    def wasm_projects(self, state=None, **kw):
        domain = [('active', '=', True)]
        if state in ('completed', 'in_progress'):
            domain.append(('state', '=', state))
        site_config = request.env['wasm.site.config'].sudo().get_config()
        page_limit = site_config.projects_page_limit if site_config and site_config.projects_page_limit > 0 else False
        projects = request.env['wasm.project'].sudo().search(domain, limit=page_limit, order='sequence, id desc')
        
        gallery_records = request.env['wasm.gallery.image'].sudo().search([('active', '=', True)], order='sequence, id')
        gallery_imgs = []
        if gallery_records:
            for g in gallery_records:
                if g.image:
                    gallery_imgs.append(f'/wasm/gallery/{g.id}/image')
                elif g.image_url:
                    gallery_imgs.append(g.image_url)
        if not gallery_imgs:
            gallery_imgs = [
                '/wasm_website/static/src/img/official_live_projects/industrial_park_sudair.webp',
                '/wasm_website/static/src/img/official_live_projects/nora_univ_1.webp',
                '/wasm_website/static/src/img/official_live_projects/nora_univ_2.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_1.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_2.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_5.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_6.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_8.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_9.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_10.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_11.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_14.webp',
                '/wasm_website/static/src/img/official_live_projects/gallery_img_17.webp',
            ]
        values = {
            'projects': projects,
            'current_state': state or 'all',
            'site_config': site_config,
            'gallery_imgs': gallery_imgs,
        }
        return request.render('wasm_website.projects_page_template', values)

    @http.route(['/projects/<int:project_id>', '/project/<int:project_id>'], type='http', auth='public', website=True)
    def wasm_project_detail(self, project_id, **kw):
        project = request.env['wasm.project'].sudo().browse(project_id)
        if not project.exists() or not project.active:
            return request.redirect('/projects')
        prev_project, next_project = project.wasm_neighbors()
        other_projects = request.env['wasm.project'].sudo().search(
            [('active', '=', True), ('id', '!=', project.id)], limit=3, order='sequence, id desc'
        )
        values = {
            'project': project,
            'prev_project': prev_project,
            'next_project': next_project,
            'other_projects': other_projects,
            'gallery_items': project.wasm_gallery_items(),
            'gallery_categories': project.wasm_gallery_categories(),
            'floor_rows': project.wasm_floor_rows(),
            'site_config': request.env['wasm.site.config'].sudo().get_config(),
        }
        return request.render('wasm_website.project_detail_page_template', values)

    @http.route('/wasm/project/<int:project_id>/media/<int:attachment_id>', type='http', auth='public')
    def wasm_project_media(self, project_id, attachment_id, **kw):
        """Images uploaded in the project's media tab (only if they belong to that project)."""
        project = request.env['wasm.project'].sudo().browse(project_id)
        if not project.exists() or not project.active or attachment_id not in project.attachment_ids.ids:
            return request.not_found()
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not (attachment.mimetype or '').startswith('image/'):
            return request.not_found()
        return self._wasm_stream(attachment, 'datas', filename=attachment.name)

    @http.route(['/contact-team', '/contact', '/contactus', '/contact-us'], type='http', auth='public', website=True)
    def wasm_contact_team(self, **kw):
        return request.render('wasm_website.contact_team_page_template', {})

    @http.route('/quote', type='http', auth='public', website=True)
    def wasm_quote(self, dept=None, service_id=None, **kw):
        services = request.env['wasm.service'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        selected_service_id = False
        if service_id and str(service_id).isdigit():
            selected_service_id = int(service_id)
        values = {
            'services': services,
            'selected_dept': dept if dept in ALLOWED_DEPARTMENTS else 'sales',
            'selected_service_id': selected_service_id,
        }
        return request.render('wasm_website.quote_page_template', values)

    @http.route('/quote/submit', type='http', auth='public', methods=['POST'],
                website=True, csrf=True)
    def wasm_quote_submit(self, **post):
        # --- Input Validation ---
        customer_name = (post.get('customer_name') or '').strip()
        phone = (post.get('phone') or '').strip()
        email = (post.get('email') or '').strip()
        project_location = (post.get('project_location') or '').strip()

        if not customer_name or not phone or not email or not project_location:
            return request.redirect('/quote?error=missing_fields')

        customer_type = post.get('customer_type', 'company')
        if customer_type not in ALLOWED_CUSTOMER_TYPES:
            customer_type = 'company'

        project_type = post.get('project_type', 'commercial')
        if project_type not in ALLOWED_PROJECT_TYPES:
            project_type = 'commercial'

        department = post.get('department', 'sales')
        if department not in ALLOWED_DEPARTMENTS:
            department = 'sales'

        details = (post.get('details') or '').strip()

        service_id = post.get('service_id')
        service_id = int(service_id) if service_id and str(service_id).isdigit() else False

        try:
            area = float(post.get('area') or 0.0)
        except (ValueError, TypeError):
            area = 0.0

        try:
            approx_budget = float(post.get('approx_budget') or 0.0)
        except (ValueError, TypeError):
            approx_budget = 0.0

        expected_start_date = post.get('expected_start_date') or False

        # --- Create Quote Request ---
        quote = request.env['wasm.quote.request'].sudo().create({
            'customer_name': customer_name,
            'phone': phone,
            'email': email,
            'customer_type': customer_type,
            'project_type': project_type,
            'project_location': project_location,
            'department': department,
            'service_id': service_id,
            'area': area,
            'approx_budget': approx_budget,
            'expected_start_date': expected_start_date,
            'details': details,
            'state': 'new',
        })

        # --- Process File Uploads (PDF, BOQ, Images) with Security Validation ---
        files = request.httprequest.files.getlist('attachments')
        attachment_ids = []
        processed_count = 0
        for uploaded_file in files:
            if not uploaded_file or not uploaded_file.filename:
                continue
            if processed_count >= MAX_FILES_COUNT:
                _logger.warning(
                    'Quote %s: File upload limit exceeded (%d max)',
                    quote.name, MAX_FILES_COUNT
                )
                break

            # Validate file extension
            _, ext = os.path.splitext(uploaded_file.filename)
            if ext.lower() not in ALLOWED_FILE_EXTENSIONS:
                _logger.warning(
                    'Quote %s: Rejected file with disallowed extension: %s',
                    quote.name, uploaded_file.filename
                )
                continue

            # Validate file size
            file_content = uploaded_file.read()
            if len(file_content) > MAX_FILE_SIZE_BYTES:
                _logger.warning(
                    'Quote %s: Rejected oversized file: %s (%d bytes)',
                    quote.name, uploaded_file.filename, len(file_content)
                )
                continue

            # Sanitize filename
            safe_filename = os.path.basename(uploaded_file.filename)

            attachment = request.env['ir.attachment'].sudo().create({
                'name': safe_filename,
                'datas': base64.b64encode(file_content),
                'res_model': 'wasm.quote.request',
                'res_id': quote.id,
            })
            attachment_ids.append(attachment.id)
            processed_count += 1

        if attachment_ids:
            quote.sudo().write({'attachment_ids': [(6, 0, attachment_ids)]})

        return request.redirect(
            '/quote/thanks?token=%s' % quote.access_token
        )

    @http.route(['/contactus/submit', '/contact/submit'], type='http', auth='public', methods=['POST'],
                website=True, csrf=True)
    def wasm_contactus_submit(self, **post):
        customer_name = (post.get('customer_name') or '').strip()
        phone = (post.get('phone') or '').strip()
        email = (post.get('email') or '').strip()
        project_location = (post.get('project_location') or 'الرياض').strip()
        details = (post.get('details') or '').strip()

        if not customer_name or not phone or not email or not details:
            return request.redirect('/contactus?error=missing_fields')

        customer_type = post.get('customer_type', 'company')
        if customer_type not in ALLOWED_CUSTOMER_TYPES:
            customer_type = 'company'

        project_type = post.get('project_type', 'commercial')
        if project_type not in ALLOWED_PROJECT_TYPES:
            project_type = 'commercial'

        department = post.get('department', 'sales')
        if department not in ALLOWED_DEPARTMENTS:
            department = 'sales'

        quote = request.env['wasm.quote.request'].sudo().create({
            'customer_name': customer_name,
            'phone': phone,
            'email': email,
            'customer_type': customer_type,
            'project_type': project_type,
            'project_location': project_location,
            'department': department,
            'details': details,
            'state': 'new',
        })

        return request.redirect(f'/quote/thanks?token={quote.access_token}')

    @http.route('/quote/thanks', type='http', auth='public', website=True)
    def wasm_quote_thanks(self, token=None, **kw):
        """Display quote confirmation page. Uses access_token for safe lookup."""
        quote = False
        if token and isinstance(token, str) and len(token) == 36:
            quote = request.env['wasm.quote.request'].sudo().search(
                [('access_token', '=', token)], limit=1
            )
        ref = quote.name if quote else None
        return request.render('wasm_website.quote_thanks_template', {
            'ref': ref,
            'quote': quote,
        })

    @http.route('/location', type='http', auth='public', website=True)
    def wasm_location(self, **kw):
        return request.render('wasm_website.location_page_template', {})

    @http.route('/robots.txt', type='http', auth='public')
    def wasm_robots_txt(self, **kw):
        robots_content = """User-agent: *
Allow: /
Allow: /services
Allow: /projects
Allow: /about-us
Allow: /our-company
Allow: /news
Allow: /contactus
Allow: /quote
Disallow: /web/login
Disallow: /web/signup
Disallow: /web/reset_password

Sitemap: https://arfa-sa.com/sitemap.xml
"""
        return request.make_response(
            robots_content,
            headers=[
                ('Content-Type', 'text/plain; charset=utf-8'),
                ('Cache-Control', 'public, max-age=86400'),
            ]
        )

    @http.route(['/news', '/our-news', '/blog', '/blog/2'], type='http', auth='public', website=True)
    def wasm_news(self, **kw):
        site_config = request.env['wasm.site.config'].sudo().get_config()
        articles = request.env['wasm.news'].sudo().search([('active', '=', True)], order='sequence, date desc, id desc')
        return request.render('wasm_website.news_page_template', {
            'site_config': site_config,
            'articles': articles,
        })

    @http.route(['/news/<int:article_id>'], type='http', auth='public', website=True)
    def wasm_news_detail(self, article_id, **kw):
        article = request.env['wasm.news'].sudo().browse(article_id)
        if not article.exists() or not article.active:
            return request.redirect('/news')
        site_config = request.env['wasm.site.config'].sudo().get_config()
        other_articles = request.env['wasm.news'].sudo().search([('active', '=', True), ('id', '!=', article.id)], limit=3, order='sequence, date desc, id desc')
        return request.render('wasm_website.news_detail_page_template', {
            'article': article,
            'other_articles': other_articles,
            'site_config': site_config,
        })

    @http.route('/wasm/news/<int:news_id>/image', type='http', auth='public')
    def wasm_news_image_stream(self, news_id, **kw):
        news = request.env['wasm.news'].sudo().browse(news_id)
        return self._wasm_stream(news, 'image',
                                 fallback_url='/wasm_website/static/src/img/project_conference_ritz.jpg')

    @http.route('/wasm/gallery/<int:image_id>/image', type='http', auth='public')
    def wasm_gallery_image_stream(self, image_id, **kw):
        img = request.env['wasm.gallery.image'].sudo().browse(image_id)
        return self._wasm_stream(img, 'image',
                                 fallback_url='/wasm_website/static/src/img/official_live_projects/gallery_img_1.webp')
