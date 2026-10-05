# -*- coding: utf-8 -*-
PAGE = 'quote'

TEXTS = [
    # ---------------- /quote : hero ----------------
    ('quote.hero.badge', 'الشارة الصغيرة أعلى البانر في صفحة طلب عرض السعر', 'OFFICIAL RFQ & QUOTATION SERVICE', 'خدمة طلب العروض والأسعار'),
    ('quote.hero.title', 'العنوان الرئيسي للبانر', 'REQUEST A QUOTE', 'طلب عرض سعر'),
    ('quote.hero.subtitle', 'النص التوضيحي تحت عنوان البانر', 'Submit Your Project Details for a Professional Technical Proposal', 'قدم تفاصيل مشروعك للحصول على عرض فني ومالي متكامل'),
    # ---------------- /quote : error messages ----------------
    ('quote.error.missing_fields', 'رسالة خطأ: حقول مطلوبة غير معبأة', 'Please fill in all required fields.', 'يرجى تعبئة جميع الحقول المطلوبة.'),
    ('quote.error.invalid_contact', 'رسالة خطأ: البريد أو الجوال غير صحيح', 'Please check the e-mail address and mobile number.', 'يرجى التأكد من البريد الإلكتروني ورقم الجوال.'),
    ('quote.error.rate_limit', 'رسالة خطأ: طلبات كثيرة خلال وقت قصير', 'Too many requests were sent. Please try again in a few minutes.', 'تم إرسال طلبات كثيرة، يرجى المحاولة بعد دقائق.'),
    ('quote.error.generic', 'رسالة خطأ عامة: تعذر إرسال الطلب', 'Your request could not be sent. Please try again.', 'تعذر إرسال الطلب، يرجى المحاولة مرة أخرى.'),
    # ---------------- /quote : client information ----------------
    ('quote.client.heading', 'عنوان قسم بيانات العميل', 'Client Information', 'بيانات العميل'),
    ('quote.form.name', 'عنوان حقل الاسم الكامل', 'Full Name *', 'الاسم الكامل *'),
    ('quote.form.phone', 'عنوان حقل رقم الجوال', 'Mobile Phone *', 'رقم الجوال *'),
    ('quote.form.phone_ph', 'النص الإرشادي داخل حقل الجوال', '05XXXXXXXX', '05XXXXXXXX'),
    ('quote.form.email', 'عنوان حقل البريد الإلكتروني', 'Email Address *', 'البريد الإلكتروني *'),
    ('quote.form.client_type', 'عنوان قائمة نوع العميل', 'Client Type', 'نوع العميل'),
    ('quote.client_type.company', 'خيار نوع العميل: شركة', 'Company / Establishment', 'شركة / مؤسسة'),
    ('quote.client_type.individual', 'خيار نوع العميل: فرد', 'Individual', 'فرد'),
    ('quote.client_type.government', 'خيار نوع العميل: جهة حكومية', 'Government Entity', 'جهة حكومية'),
    ('quote.form.department', 'عنوان قائمة القسم المختص', 'Target Department', 'القسم المختص'),
    ('quote.dept.sales', 'خيار القسم: المبيعات', 'Sales', 'المبيعات'),
    ('quote.dept.engineering', 'خيار القسم: الهندسة', 'Engineering', 'الهندسة'),
    ('quote.dept.projects', 'خيار القسم: المشاريع', 'Projects', 'المشاريع'),
    ('quote.dept.hr', 'خيار القسم: الموارد البشرية', 'Human Resources', 'الموارد البشرية'),
    ('quote.dept.management', 'خيار القسم: الإدارة', 'Management', 'الإدارة'),
    # ---------------- /quote : project details ----------------
    ('quote.project.heading', 'عنوان قسم تفاصيل المشروع', 'Project Details', 'تفاصيل المشروع'),
    ('quote.form.project_type', 'عنوان قائمة نوع المشروع', 'Project Type *', 'نوع المشروع *'),
    ('quote.ptype.commercial', 'خيار نوع المشروع: تجاري', 'Commercial', 'تجاري'),
    ('quote.ptype.residential', 'خيار نوع المشروع: سكني', 'Residential', 'سكني'),
    ('quote.ptype.industrial', 'خيار نوع المشروع: صناعي', 'Industrial', 'صناعي'),
    ('quote.ptype.infrastructure', 'خيار نوع المشروع: بنية تحتية', 'Infrastructure', 'بنية تحتية'),
    ('quote.ptype.renovation', 'خيار نوع المشروع: ترميم وتجديد', 'Renovation', 'ترميم وتجديد'),
    ('quote.form.location', 'عنوان حقل موقع المشروع', 'Project Location *', 'موقع المشروع *'),
    ('quote.form.service', 'عنوان قائمة الخدمة المطلوبة', 'Requested Service', 'الخدمة المطلوبة'),
    ('quote.form.service_ph', 'الخيار الأول الفارغ في قائمة الخدمات', '-- Select Service --', '-- اختر الخدمة --'),
    ('quote.form.area', 'عنوان حقل المساحة', 'Area (m²)', 'المساحة (م²)'),
    ('quote.form.budget', 'عنوان حقل الميزانية', 'Budget (SAR)', 'الميزانية (ريال سعودي)'),
    ('quote.form.start_date', 'عنوان حقل تاريخ البدء المتوقع', 'Expected Start Date', 'تاريخ البدء المتوقع'),
    ('quote.form.details', 'عنوان حقل تفاصيل المشروع والملاحظات', 'Project Details & Notes', 'تفاصيل المشروع والملاحظات'),
    # ---------------- /quote : attachments + submit ----------------
    ('quote.files.heading', 'عنوان قسم إرفاق المخططات', 'Drawings & Documents Attachment', 'إرفاق المخططات والمستندات'),
    ('quote.files.button', 'زر اختيار الملفات', 'Choose Files', 'اختر الملفات'),
    ('quote.files.hint', 'النص تحت زر اختيار الملفات (أنواع الملفات)', 'PDF, CAD drawings, BOQ spreadsheets', 'ملفات PDF، مخططات CAD، جداول الكميات'),
    ('quote.files.selected', 'عنوان قائمة الملفات المختارة ({n} = عدد الملفات)', 'Selected files for upload ({n}):', 'الملفات المحددة للرفع ({n}):'),
    ('quote.form.submit', 'زر إرسال الطلب', 'Submit RFQ', 'إرسال الطلب'),
    ('quote.form.submitting', 'نص الزر أثناء الإرسال', 'Submitting RFQ & saving attachments...', 'جاري إرسال الطلب وحفظ المرفقات...'),
    # ---------------- /quote/thanks ----------------
    ('quote.thanks.heading', 'عنوان صفحة الشكر بعد إرسال الطلب', 'Request Submitted Successfully!', 'تم إرسال طلبك بنجاح!'),
    ('quote.thanks.message', 'رسالة الشكر بعد إرسال الطلب', 'Thank you for reaching out to ARFA SPECIALIZED SYSTEMS. Our engineering team will contact you shortly.', 'شكراً لتواصلك مع شركة عرفة للأنظمة المتخصصة. سيتواصل معك فريقنا الهندسي قريباً.'),
    ('quote.thanks.ref_label', 'عنوان رقم المرجع في صفحة الشكر', 'Reference Number:', 'رقم المرجع:'),
    ('quote.thanks.home', 'زر العودة للرئيسية في صفحة الشكر', 'Return to Home', 'العودة إلى الرئيسية'),

    # ---------------- /news ----------------
    ('news.hero.badge', 'الشارة الصغيرة أعلى البانر في صفحة الأخبار', 'NEWS & MEDIA', 'الأخبار والأنشطة'),
    ('news.hero.title', 'العنوان الرئيسي لبانر الأخبار', 'LATEST NEWS & ANNOUNCEMENTS', 'أحدث الأخبار والإعلانات'),
    ('news.hero.subtitle', 'النص التوضيحي تحت عنوان بانر الأخبار', 'Stay updated with ARFA engineering milestones, project developments, and Saudi Building Code (SBC) updates', 'متابعة لأحدث إنجازات شركة عرفة والأنظمة المتخصصة وأخبار الكود السعودي للمباني'),
    ('news.card.read', 'زر قراءة الخبر في بطاقة الخبر', 'Read Article', 'اقرأ التفاصيل'),
    ('news.empty', 'رسالة تظهر عند عدم وجود أخبار منشورة', 'No news has been published yet. Please check back soon.', 'لا توجد أخبار منشورة حالياً، يرجى العودة لاحقاً.'),
    # ---------------- /news/<id> ----------------
    ('news.detail.badge', 'الشارة أعلى بانر الخبر إذا لم يكن له تصنيف', 'NEWS & MEDIA', 'الأخبار والأنشطة'),
    ('news.detail.published', 'كلمة "نُشر" قبل تاريخ الخبر في البانر', 'Published:', 'نُشر بتاريخ:'),
    ('news.detail.back', 'زر العودة لقائمة الأخبار', 'Back to News', 'العودة للأخبار'),
]

ITEMS = [
]

# Sample articles created by the setup when the news table is empty (same 5 cards that the
# /news page showed before news became editable). `name` / `summary` / `content` are Arabic,
# `*_en` English. `image_file` = image inside the module, uploaded into the record.
NEWS = [
    {
        'name': 'اكتمال الأعمال الهندسية والكهروميكانيكية لمشروع فندق ريتز كارلتون بالرياض',
        'title_en': 'Completion of MEP & Smart HVAC Infrastructure for Ritz-Carlton Project',
        'summary': 'أعلنت شركة عرفة للأنظمة المتخصصة عن استكمال وتسليم كافة شبكات الكهروميكانيك (MEP)، والتكييف المركزي، وأنظمة التحكم الذكي (BMS) لمجمع قاعات الفندق وفق أعلى مواصفات كود البناء السعودي.',
        'summary_en': 'ARFA Specialized Systems announces the successful delivery of advanced electromechanical networks, central HVAC, and integrated smart BMS for the conference hall complex adhering strictly to Saudi Building Code (SBC) standard requirements.',
        'content': (
            '<p>أنهت شركة عرفة للأنظمة المتخصصة أعمال الكهروميكانيك (MEP) في مجمع قاعات المؤتمرات بمشروع فندق ريتز كارلتون بالرياض، وشملت الأعمال شبكات الكهرباء والتمديدات الميكانيكية ومنظومة التكييف المركزي.</p>'
            '<p>كما تم ربط أنظمة التكييف والإنارة والتهوية بنظام إدارة المبنى الذكي (BMS) الذي يتيح لفريق تشغيل الفندق مراقبة الأنظمة والتحكم بها من نقطة واحدة.</p>'
            '<p>نُفذت جميع الأعمال واختبرت وفق متطلبات كود البناء السعودي (SBC) قبل تسليمها للمالك.</p>'
        ),
        'content_en': (
            '<p>ARFA Specialized Systems has completed the electromechanical (MEP) works for the conference hall complex of the Ritz-Carlton project in Riyadh. The scope covered the power distribution networks, mechanical installations and the central HVAC system serving the halls.</p>'
            '<p>The HVAC, lighting and ventilation systems were integrated into a smart Building Management System (BMS), giving the hotel operations team a single point to monitor and control the building services.</p>'
            '<p>All works were installed, tested and commissioned in line with the requirements of the Saudi Building Code (SBC) before handover to the client.</p>'
        ),
        'category': 'projects',
        'badge_en': 'Project Milestone',
        'badge_ar': 'إنجازات المشاريع',
        'date': '2026-08-15',
        'author': 'ARFA Media Office',
        'image_file': 'static/src/img/project_conference_ritz.jpg',
        'sequence': 10,
    },
    {
        'name': 'اعتماد تقنيات النمذجة ثلاثية الأبعاد (BIM) المتقدمة في كافة مشاريع عام 2026م',
        'title_en': 'Expanding 3D BIM Building Information Modeling across All 2026 Developments',
        'summary': 'تطبيق منصات النمذجة المتقدمة (BIM) لرفع التنسيق الهندسي بين قطاعات التخطيط الإنشائي، والمعماري، والتركيبات الميكانيكية، مما ساهم في منع التضاربات وإلغاء أي تعديلات بالمنشآت.',
        'summary_en': 'Integration of state-of-the-art 3D BIM technology streamlines cross-departmental coordination between structural civil engineering, architectural layouts, and MEP installations, eliminating site clashes and reducing rework.',
        'content': (
            '<p>تعتمد شركة عرفة نمذجة معلومات البناء ثلاثية الأبعاد (BIM) في جميع مشاريعها لعام 2026م، حيث تُجمع النماذج الإنشائية والمعمارية ونماذج الأعمال الكهروميكانيكية في نموذج تنسيقي واحد.</p>'
            '<p>يتيح ذلك اكتشاف التعارضات بين العناصر الإنشائية ومسارات التمديدات قبل بدء التنفيذ في الموقع، مما يقلل إعادة العمل ويختصر وقت التنفيذ.</p>'
            '<p>كما تُستخدم النماذج في استخراج الكميات وإعداد مخططات التنفيذ، وتُحدّث حتى التسليم لتصبح مرجعاً لأعمال التشغيل والصيانة.</p>'
        ),
        'content_en': (
            '<p>ARFA is applying 3D Building Information Modeling (BIM) across all of its 2026 developments. Structural, architectural and MEP models are combined into one federated coordination model shared by the project teams.</p>'
            '<p>Clash detection on the combined model reveals conflicts between structural elements and service routes before work starts on site, which reduces rework and keeps installation schedules on track.</p>'
            '<p>The models are also used for quantity take-off and shop drawings, and are kept up to date until handover so that they can serve as a reference for operation and maintenance.</p>'
        ),
        'category': 'engineering',
        'badge_en': 'Engineering Innovation',
        'badge_ar': 'الابتكار والتطوير',
        'date': '2026-07-28',
        'author': 'Engineering Tech',
        'image_file': 'static/src/img/why_bim.jpg',
        'sequence': 20,
    },
    {
        'name': 'تجديد اعتماد وتراخيص السلامة الوقائية ومكافحة الحريق مع الدفاع المدني',
        'title_en': 'Full Civil Defense Safety Certification Renewal for ARFA Contracting Operations',
        'summary': 'حصلت فرق ومشاريع شركة عرفة على التراخيص المحدثة وفق كود السلامة والوقاية من الحريق المعتمد لحماية الأرواح والمنشآت.',
        'summary_en': 'Re-certifying all fire alarm, automatic sprinkler systems, and safety engineering teams according to updated Saudi Civil Defense standards.',
        'content': (
            '<p>جددت شركة عرفة اعتماداتها وتراخيصها لدى المديرية العامة للدفاع المدني في مجال أنظمة السلامة والوقاية من الحريق.</p>'
            '<p>شمل التجديد أعمال تصميم وتركيب وصيانة أنظمة إنذار الحريق وشبكات الرش الآلي، إضافة إلى اعتماد فرق هندسة السلامة العاملة في مشاريع الشركة.</p>'
            '<p>ويضمن ذلك تنفيذ أنظمة الحماية من الحريق في مشاريع عملائنا وفق أحدث متطلبات الدفاع المدني وكود الحماية من الحريق السعودي.</p>'
        ),
        'content_en': (
            '<p>ARFA has renewed its Saudi Civil Defense certifications for fire safety and fire protection works.</p>'
            '<p>The renewal covers the design, installation and maintenance of fire alarm systems and automatic sprinkler networks, as well as the certification of the safety engineering teams working on the company\'s sites.</p>'
            '<p>It ensures that the fire protection systems delivered to our clients meet the latest Civil Defense requirements and the Saudi Fire Code.</p>'
        ),
        'category': 'safety',
        'badge_en': 'Safety & Compliance',
        'badge_ar': 'السلامة والجودة',
        'date': '2026-06-10',
        'author': 'ARFA Media Office',
        'image_file': 'static/src/img/why_safety.jpg',
        'sequence': 30,
    },
    {
        'name': 'توسع قطاع حلول الطاقة الشمسية الكهروضوئية للمصانع والمنشآت الصناعية',
        'title_en': 'Expansion of Solar PV & Clean Energy Solutions for Industrial Facilities',
        'summary': 'توقيع عقود جديدة لتنفيذ شبكات الطاقة الشمسية ومحولات الطاقة الهجينة لتقليل التكلفة التشغيلية بالمدن الصناعية.',
        'summary_en': 'Signing new supply contracts for commercial PV solar systems and energy storage in Sudair Industrial City.',
        'content': (
            '<p>وقعت شركة عرفة عقوداً جديدة لتوريد وتركيب أنظمة الطاقة الشمسية الكهروضوئية التجارية وحلول تخزين الطاقة لمنشآت صناعية في مدينة سدير الصناعية.</p>'
            '<p>تشمل الأعمال الألواح الشمسية والعواكس الهجينة وأنظمة التخزين بالبطاريات وربطها بالشبكات الكهربائية القائمة في المصانع.</p>'
            '<p>تساعد هذه الحلول المنشآت الصناعية على خفض تكاليف التشغيل والاستهلاك من الشبكة، وتدعم مستهدفات الطاقة المتجددة في المملكة.</p>'
        ),
        'content_en': (
            '<p>ARFA has signed new contracts to supply and install commercial solar PV systems and energy storage for industrial facilities in Sudair Industrial City.</p>'
            '<p>The scope includes the PV arrays, hybrid inverters and battery storage, together with their connection to the existing electrical networks of the factories.</p>'
            '<p>These systems help industrial clients lower their operating costs and grid consumption, in support of the Kingdom\'s renewable energy targets.</p>'
        ),
        'category': 'sustainability',
        'badge_en': 'Green Energy',
        'badge_ar': 'الطاقة المستدامة',
        'date': '2026-05-02',
        'author': 'ARFA Media Office',
        'image_file': 'static/src/img/project_sudair_industrial.jpg',
        'sequence': 40,
    },
    {
        'name': 'إجراءات الرقابة واختبارات الجودة للمواد الخرسانية والمعادن بالموقع',
        'title_en': 'Rigorous On-site Quality Inspections & Material Testing Workflows',
        'summary': 'التزام تام بالفحوصات المختبرية اليومية للتربة والخرسانات المسلحة لضمان أطول عمر افتراضي للمباني.',
        'summary_en': 'Enforcing strict daily quality control protocols and independent soil/material lab tests across all building sites.',
        'content': (
            '<p>تطبق شركة عرفة إجراءات يومية لضبط الجودة في جميع مواقع البناء، تبدأ من فحص المواد عند استلامها وتستمر في كل مرحلة من مراحل التنفيذ.</p>'
            '<p>تُرسل عينات التربة والخرسانة وحديد التسليح إلى مختبرات مستقلة معتمدة، ولا يُعتمد أي بند إلا بعد مطابقة النتائج للمواصفات وكود البناء السعودي.</p>'
            '<p>وتوثق نتائج الفحوصات والاختبارات في سجلات الجودة لكل مشروع وتسلم للعميل مع ملفات التسليم.</p>'
        ),
        'content_en': (
            '<p>ARFA enforces daily quality control procedures on all of its building sites, starting with the inspection of materials on delivery and continuing through every stage of construction.</p>'
            '<p>Soil, concrete and reinforcement steel samples are tested by independent accredited laboratories, and no work item is approved until the results comply with the specifications and the Saudi Building Code (SBC).</p>'
            '<p>All inspection and test results are recorded in the project quality records and handed over to the client with the project documentation.</p>'
        ),
        'category': 'quality',
        'badge_en': 'SBC Standards',
        'badge_ar': 'كود البناء السعودي',
        'date': '2026-03-18',
        'author': 'ARFA Media Office',
        'image_file': 'static/src/img/why_qc.jpg',
        'sequence': 50,
    },
]
