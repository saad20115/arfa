# -*- coding: utf-8 -*-
"""Footer, floating contact buttons and AI chat assistant (shown on every page)."""
PAGE = 'layout'

TEXTS = [
    # ---- Footer --------------------------------------------------------
    ('layout.footer.logo_alt', 'وصف شعار الفوتر (للقارئات الصوتية ومحركات البحث)',
     'ARFA Construction & Specialized Systems', 'شركة عرفة للأنظمة المتخصصة'),
    ('layout.footer.desc', 'نبذة الشركة أسفل شعار الفوتر',
     'Leading Saudi general contracting firm specializing in structural, civil, and MEP engineering works following the Saudi Building Code.',
     'شركة مقاولات عامة سعودية رائدة متخصصة في الأعمال الإنشائية والمدنية والكهروميكانيكية وفق كود البناء السعودي.',
     True),
    ('layout.footer.links_title', 'عنوان عمود الروابط السريعة في الفوتر', 'Quick Links', 'روابط سريعة'),
    ('layout.footer.depts_title', 'عنوان عمود الأقسام في الفوتر', 'Departments', 'الأقسام'),
    ('layout.footer.contact_title', 'عنوان عمود بيانات التواصل في الفوتر', 'Contact Us', 'تواصل معنا'),
    ('layout.footer.quote_btn', 'زر طلب عرض السعر في الفوتر', 'Request a Quote', 'اطلب عرض سعر'),
    ('layout.footer.copyright', 'سطر حقوق النشر أسفل الفوتر (اكتب السنة بنفسك)',
     '© 2026 ARFA SPECIALIZED SYSTEMS - All Rights Reserved', '© 2026 عرفة للأنظمة المتخصصة - جميع الحقوق محفوظة'),
    ('layout.footer.totop', 'زر العودة للأعلى في أسفل الفوتر', 'Back to Top', 'العودة للأعلى'),

    # ---- Floating buttons (bottom corner) ------------------------------
    ('layout.float.toggle_title', 'تلميح الزر العائم الرئيسي (عند مرور الماوس)', 'Contact Us', 'تواصل معنا'),
    ('layout.float.toggle_aria', 'وصف الزر العائم الرئيسي للقارئات الصوتية', 'Toggle Menu', 'فتح أو إغلاق القائمة'),
    ('layout.float.bot_title', 'تلميح زر المساعد الذكي العائم', 'AI Assistant', 'المساعد الذكي'),
    ('layout.float.whatsapp_title', 'تلميح زر الواتساب العائم', 'WhatsApp Chat', 'محادثة واتساب'),
    ('layout.float.quote_title', 'تلميح زر طلب عرض السعر العائم', 'Request Quote', 'طلب عرض سعر'),
    ('layout.totop_aria', 'وصف زر العودة لأعلى الصفحة للقارئات الصوتية', 'Back to top', 'العودة للأعلى'),

    # ---- AI chat assistant ---------------------------------------------
    ('bot.header.title', 'اسم المساعد الذكي في رأس نافذة المحادثة',
     'ARFA AI Engineering Assistant', 'مساعد عرفة الهندسي الذكي'),
    ('bot.header.status', 'الحالة أسفل اسم المساعد', 'Online • Instant Answer', 'متصل • رد فوري'),
    ('bot.close_aria', 'وصف زر إغلاق نافذة المحادثة للقارئات الصوتية', 'Close chat', 'إغلاق المحادثة'),
    ('bot.welcome', 'رسالة الترحيب في بداية المحادثة',
     'Welcome to ARFA SPECIALIZED SYSTEMS! 🏗️ I am your AI Engineering Assistant. How can I help you today?',
     'مرحباً بك في شركة عرفة للأنظمة المتخصصة! 🏗️ أنا مساعدك الهندسي الذكي. كيف يمكنني مساعدتك اليوم؟',
     True),
    ('bot.input.placeholder', 'النص الإرشادي داخل خانة كتابة السؤال',
     'Ask any question about your project...', 'اكتب أي سؤال عن مشروعك...'),
    ('bot.input.aria', 'وصف خانة كتابة السؤال للقارئات الصوتية', 'Ask ARFA AI', 'اسأل مساعد عرفة'),
    ('bot.send_aria', 'وصف زر إرسال السؤال للقارئات الصوتية', 'Send', 'إرسال'),
]

ITEMS = [
    # ---- Footer: quick links ----
    {'section': 'footer_link', 'title_en': 'Home', 'title_ar': 'الرئيسية', 'link_url': '/'},
    {'section': 'footer_link', 'title_en': 'About Us', 'title_ar': 'من نحن', 'link_url': '/about'},
    {'section': 'footer_link', 'title_en': 'Services', 'title_ar': 'الخدمات', 'link_url': '/services'},
    {'section': 'footer_link', 'title_en': 'Projects', 'title_ar': 'المشاريع', 'link_url': '/projects'},

    # ---- Footer: departments ----
    {'section': 'footer_dept', 'title_en': 'Engineering & Design', 'title_ar': 'الهندسة والتصميم',
     'link_url': '/quote?dept=engineering'},
    {'section': 'footer_dept', 'title_en': 'Sales & Pricing', 'title_ar': 'المبيعات والتسعير',
     'link_url': '/quote?dept=sales'},
    {'section': 'footer_dept', 'title_en': 'Project Management', 'title_ar': 'إدارة المشاريع',
     'link_url': '/quote?dept=projects'},
    {'section': 'footer_dept', 'title_en': 'All Departments', 'title_ar': 'جميع الأقسام',
     'link_url': '/contact-team'},

    # ---- AI assistant: quick question buttons (title = button text, description = question sent) ----
    {'section': 'bot_chip', 'title_en': '📋 Request Project Quote', 'title_ar': '📋 طلب عرض سعر لمشروع',
     'desc_en': 'Request project quote', 'desc_ar': 'طلب عرض سعر لمشروعي'},
    {'section': 'bot_chip', 'title_en': '🏗️ Saudi Building Code (SBC)', 'title_ar': '🏗️ كود البناء السعودي (SBC)',
     'desc_en': 'Saudi Building Code SBC', 'desc_ar': 'كود البناء السعودي SBC'},
    {'section': 'bot_chip', 'title_en': '⚡ MEP & Central HVAC', 'title_ar': '⚡ الأعمال الكهروميكانيكية والتكييف المركزي',
     'desc_en': 'MEP and Central HVAC', 'desc_ar': 'الأعمال الكهروميكانيكية والتكييف المركزي MEP'},
    {'section': 'bot_chip', 'title_en': '📞 Engineering Consultation', 'title_ar': '📞 استشارة هندسية',
     'desc_en': 'Direct engineering consultation', 'desc_ar': 'استشارة هندسية مباشرة'},

    # ---- AI assistant: answers ----
    # subtitle = keywords (comma separated, any language); the first answer (in display order) whose
    # keyword appears in the question is used. An answer with NO keywords is the default answer.
    # In the answer: one paragraph per line, lines starting with "•" or "-" become a bullet list,
    # web addresses / e-mails become links, {phone} {mobile} {whatsapp} {email} are replaced by the
    # contact data of the site settings (a line whose placeholder is empty is skipped).
    {'section': 'bot_reply', 'title_en': 'Quotation request', 'title_ar': 'طلب عرض سعر',
     'subtitle_en': 'quote, price, rfq, cost', 'subtitle_ar': 'سعر, عرض, تكلفة, طلب',
     'desc_en': 'We are delighted to prepare a detailed engineering quotation for your project! 📋\n'
                'Please fill out our quick online RFQ form to route your drawings to our estimating team:',
     'desc_ar': 'يسعدنا تقديم عرض سعر تفصيلي لمشروعك وفق الكود السعودي! 📋\n'
                'يمكنك تعبئة النموذج الإلكتروني السريع وسيتم تحويله فوراً لفريق التسعير والدراسات الهندسية:',
     'link_url': '/quote', 'link_label_en': 'Proceed to RFQ Form', 'link_label_ar': 'الانتقال لنموذج طلب عرض السعر'},
    {'section': 'bot_reply', 'title_en': 'Saudi Building Code (SBC)', 'title_ar': 'كود البناء السعودي',
     'subtitle_en': 'sbc, code, saudi', 'subtitle_ar': 'كود, سعودي, معايير, سلامة',
     'desc_en': 'ARFA Construction & Specialized Systems strictly adheres to the Saudi Building Code (SBC 301 - SBC 306) 🏗️\n'
                'We guarantee full structural compliance, certified concrete testing, and rigid safety quality control '
                'for every construction milestone.',
     'desc_ar': 'تلتزم شركة عرفة للأنظمة المتخصصة بالمرجع القياسي: الكود السعودي للبناء (SBC 301 - SBC 306) 🏗️\n'
                'نضمن لك أعلى درجات السلامة الإنشائية، والخرسانات المعتمدة، واختبارات الجودة المخبرية لكل مرحلة بناء.'},
    {'section': 'bot_reply', 'title_en': 'MEP & HVAC', 'title_ar': 'الأعمال الكهروميكانيكية والتكييف',
     'subtitle_en': 'mep, hvac, cooling, fire', 'subtitle_ar': 'تكييف, كهرباء, كهروميكانيك, سباكة, حريق',
     'desc_en': 'We provide integrated MEP & Central HVAC solutions including: ⚡\n'
                '• Central Air Conditioning & Ducting (VRF / Chilled Water)\n'
                '• Civil Defense Certified Firefighting & Alarm Systems\n'
                '• Advanced Plumbing, Water Pumps & Drainage Infrastructure\n'
                '• High Voltage Electrical Distribution & Substation Panels',
     'desc_ar': 'نوفر حلولاً كهروميكانيكية متكاملة (MEP Systems) تشمل: ⚡\n'
                '• أنظمة التكييف المركزي والدكت (VRF / Chilled Water)\n'
                '• شبكات مكافحة الحريق والإنذار المبكر المعتمدة من الدفاع المدني\n'
                '• شبكات السباكة والتغذية المائية والصرف المتقدمة\n'
                '• لوحات توزيع الكهرباء والمحطات الفرعية',
     'link_url': '/services', 'link_label_en': 'Explore MEP Services', 'link_label_ar': 'استعراض كافة الخدمات'},
    {'section': 'bot_reply', 'title_en': 'Contact an engineer', 'title_ar': 'التواصل مع مهندس',
     'subtitle_en': 'contact, phone, whatsapp, call, consultation',
     'subtitle_ar': 'تواصل, اتصال, واتساب, مهندس, استشارة',
     'desc_en': 'You can connect directly with our project engineers on WhatsApp: 🟢\n'
                'Or call us directly: {phone}\n'
                'E-mail: {email}',
     'desc_ar': 'يمكنك التواصل المباشر مع المهندس المختص عبر الواتساب فوراً: 🟢\n'
                'أو عبر الهاتف: {phone}\n'
                'البريد الإلكتروني: {email}',
     'link_url': '{whatsapp}', 'link_label_en': 'Direct WhatsApp Chat', 'link_label_ar': 'محادثة واتساب مباشرة'},
    {'section': 'bot_reply', 'title_en': 'Projects', 'title_ar': 'المشاريع',
     'subtitle_en': 'projects, portfolio, work', 'subtitle_ar': 'مشروع, مشاريع, معرض, أعمال',
     'desc_en': 'ARFA has successfully delivered major commercial, residential, and infrastructure projects '
                'across Saudi Arabia! 🏢',
     'desc_ar': 'نفذت شركة عرفة مشاريع كبرى تجارية وسكنية ومشاريع بنية تحتية في مختلف مناطق المملكة! 🏢',
     'link_url': '/projects', 'link_label_en': 'Browse Projects Portfolio', 'link_label_ar': 'تصفح معرض المشاريع المنفذة'},
    {'section': 'bot_reply', 'title_en': 'Default answer (no keyword matched)', 'title_ar': 'الرد الافتراضي',
     'desc_en': 'Thank you for reaching out to the ARFA AI Engineering Assistant! 🏗️\n'
                'We stand ready to execute your structural building, MEP systems, and luxury architectural fitouts '
                'with uncompromised precision.\n'
                'WhatsApp: {whatsapp}',
     'desc_ar': 'شكراً لتواصلك مع مساعد عرفة الهندسي الذكي! 🏗️\n'
                'نحن متأهبون لتنفيذ مشاريع المباني الإنشائية، والتشطيبات الفاخرة، والحلول الكهروميكانيكية (MEP) '
                'بأعلى درجات الدقة.\n'
                'واتساب: {whatsapp}',
     'link_url': '/quote', 'link_label_en': 'Request Quote', 'link_label_ar': 'طلب عرض سعر'},
]
