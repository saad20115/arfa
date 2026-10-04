# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID

def post_init_hook(env):
    """
    Hook to clean up website menus and create standard, non-duplicated,
    bilingual navigation menus (Arabic & English) for Wasm Contracting Co.
    """
    WebsiteMenu = env['website.menu']
    
    # 1. Unlink specific unwanted default menus without destroying other apps' menus
    unwanted = WebsiteMenu.search([('url', 'in', ['/shop', '/jobs', '/contactus', '/blog', '/event'])])
    unwanted.unlink()

    top_menu = WebsiteMenu.search([('website_id', '=', 1), ('parent_id', '=', False)], limit=1)
    if not top_menu:
        top_menu = WebsiteMenu.search([('parent_id', '=', False)], limit=1)
        
    if top_menu:
        top_level_menus = [
            ({'en_US': 'Home', 'ar_001': 'الرئيسية'}, '/', 10),
            ({'en_US': 'About Us', 'ar_001': 'عن الشركة'}, '/about', 20),
            ({'en_US': 'Services', 'ar_001': 'خدماتنا'}, '/services', 30),
            ({'en_US': 'Projects', 'ar_001': 'مشاريعنا'}, '/projects', 40),
            ({'en_US': 'Company Divisions', 'ar_001': 'أقسام الشركة'}, '/contact-team', 50),
            ({'en_US': 'Request a Quote', 'ar_001': 'طلب عرض سعر'}, '/quote', 60),
            ({'en_US': 'Contact Us', 'ar_001': 'تواصل معنا'}, '/contactus', 70),
        ]

        services_sub_menus = [
            ({'en_US': 'Planning & Structural Construction', 'ar_001': 'التخطيط والإنشاءات الخرسانية'}, '/planning-construction', 10),
            ({'en_US': 'Modern Building Systems', 'ar_001': 'أنظمة البناء الحديثة'}, '/modern-building-systems', 20),
            ({'en_US': 'Electromechanical MEP', 'ar_001': 'أنظمة الكهروميكانيك MEP'}, '/electromechanical-systems', 30),
            ({'en_US': 'Smart BMS Automation', 'ar_001': 'المباني الذكية BMS'}, '/smart-building-systems', 40),
            ({'en_US': 'Alternative Energy Solutions', 'ar_001': 'حلول الطاقة البديلة'}, '/alternative-energy-solutions', 50),
            ({'en_US': 'Fire Protection & Prevention', 'ar_001': 'أنظمة الإطفاء والوقاية من الحريق'}, '/fire-protection-prevention-systems', 60),
            ({'en_US': 'Medical Gas Systems', 'ar_001': 'أنظمة الغازات الطبية'}, '/medical-gas-systems', 70),
            ({'en_US': 'Infrastructure Development', 'ar_001': 'تطوير البنية التحتية'}, '/infrastructure-development', 80),
        ]
        
        services_menu = False
        for name_dict, url, seq in top_level_menus:
            m = WebsiteMenu.create({
                'name': name_dict,
                'url': url,
                'sequence': seq,
                'parent_id': top_menu.id,
                'website_id': 1,
            })
            if url == '/services':
                services_menu = m

        if services_menu:
            for name_dict, url, seq in services_sub_menus:
                WebsiteMenu.create({
                    'name': name_dict,
                    'url': url,
                    'sequence': seq,
                    'parent_id': services_menu.id,
                    'website_id': 1,
                })

