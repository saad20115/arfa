# -*- coding: utf-8 -*-
{
    'name': 'شركة عرفة الهندسية - الموقع الإلكتروني وإدارة الطلبات',
    'summary': 'موقع إلكتروني رسمي واحترافي لشركة عرفة الهندسية مع نظام استقبال وربط طلبات عروض الأسعار والمعرض والمشاريع',
    'description': """
شركة عرفة الهندسية - ARFA SPECIALIZED SYSTEMS Website & Quote Management System
================================================================================
- الموقع الإلكتروني الرسمي المتكامل (8 صفحات تفاعلية).
- نموذج طلب عرض السعر الإلكتروني مع الترقيم المرجعي وتتبع الحالات الـ 7.
- معرض المشاريع والخدمات الإنشائية والكهروميكانيكية.
- توجيه الطلبات للأقسام المختصة (هندسة، مبيعات، مشاريع، موارد بشرية، إدارة).
- لوحة تحكم كاملة لإدارة الطلبات والمشاريع والعملاء.
    """,
    'author': 'ARFA SPECIALIZED SYSTEMS',
    'website': 'https://arfa-sa.com',
    'category': 'Website/Website',
    'version': '19.0.1.1.2',
    'depends': ['base', 'web', 'website', 'mail'],
    'data': [
        'security/wasm_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/wasm_demo_data.xml',
        'views/quote_request_views.xml',
        'views/wasm_project_views.xml',
        'views/wasm_service_views.xml',
        'views/wasm_site_config_views.xml',
        'views/wasm_partner_views.xml',
        'views/wasm_testimonial_views.xml',
        'views/wasm_news_views.xml',
        'views/wasm_gallery_views.xml',
        'views/wasm_menus.xml',
        'views_templates/website_templates.xml',
        'data/wasm_pages_data.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'wasm_website/static/src/css/wasm_style.css',
            'wasm_website/static/src/js/wasm_quote.js',
            'wasm_website/static/src/js/wasm_slider.js',
            'wasm_website/static/src/js/wasm_ai_bot.js',
            'wasm_website/static/src/js/wasm_video_player.js',
            'wasm_website/static/src/js/wasm_typewriter.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
    'license': 'LGPL-3',
}
