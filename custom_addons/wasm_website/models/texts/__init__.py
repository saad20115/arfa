# -*- coding: utf-8 -*-
"""Default content of the website (texts + repeated items).

Each page group has its own file exposing:

* ``TEXTS``: list of tuples ``(key, label, en, ar)`` or ``(key, label, en, ar, True)``
  (the trailing ``True`` marks a multi-line text). The page of every key is the
  file's ``PAGE`` unless the key is listed in ``PAGE_OF`` ({key: page}).
* ``ITEMS``: list of dicts used to seed ``wasm.content.item`` records the first
  time a section is empty (keys: section, title_en, title_ar, subtitle_en,
  subtitle_ar, desc_en, desc_ar, badge_en, badge_ar, value, icon, link_url,
  link_label_en, link_label_ar, image_url, image_file (path inside the module)).
"""
from . import t_layout, t_home, t_company, t_quote_news, t_projects_services, t_seed_core, t_seo

PAGES = [
    ('layout', 'عام: الهيدر والفوتر'),
    ('home', 'الصفحة الرئيسية'),
    ('about', 'من نحن'),
    ('company', 'شركتنا'),
    ('contact', 'تواصل معنا'),
    ('location', 'موقعنا'),
    ('services', 'الخدمات'),
    ('service_detail', 'صفحة الخدمة'),
    ('projects', 'المشاريع'),
    ('project_detail', 'صفحة المشروع'),
    ('quote', 'طلب عرض سعر'),
    ('news', 'الأخبار'),
    ('bot', 'المساعد الذكي'),
    ('seo', 'محركات البحث'),
]
_PAGE_KEYS = {p for p, _ in PAGES}

TEXT_DEFAULTS = {}
ITEM_SEEDS = []
for _mod in (t_seed_core, t_layout, t_home, t_company, t_quote_news, t_projects_services, t_seo):
    _page_of = getattr(_mod, 'PAGE_OF', {})
    for _row in getattr(_mod, 'TEXTS', []):
        _key, _label, _en, _ar = _row[:4]
        _page = _page_of.get(_key) or (_key.split('.', 1)[0] if _key.split('.', 1)[0] in _PAGE_KEYS else _mod.PAGE)
        if _key in TEXT_DEFAULTS:
            raise ValueError('Duplicate website text key: %s' % _key)
        TEXT_DEFAULTS[_key] = {'page': _page, 'label': _label, 'en': _en or '', 'ar': _ar or '',
                               'multiline': bool(_row[4]) if len(_row) > 4 else ('\n' in (_en or '') or len(_en or '') > 120)}
    ITEM_SEEDS.extend(getattr(_mod, 'ITEMS', []))
