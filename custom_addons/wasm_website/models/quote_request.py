# -*- coding: utf-8 -*-
import logging
import uuid
from datetime import timedelta

from markupsafe import escape
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class WasmQuoteRequest(models.Model):
    _name = 'wasm.quote.request'
    _description = 'طلب عرض سعر - شركة عرفة الهندسية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(
        string='الرقم المرجعي للطلب',
        required=True,
        readonly=True,
        default='New',
        copy=False,
        tracking=True
    )
    access_token = fields.Char(
        string='رمز الوصول الآمن',
        readonly=True,
        copy=False,
        index=True,
        default=lambda self: str(uuid.uuid4()),
        help='رمز فريد يُستخدم للتحقق من هوية صاحب الطلب في الروابط العامة',
    )
    customer_name = fields.Char(string='اسم العميل', required=True, tracking=True)
    phone = fields.Char(string='رقم الجوال', required=True, tracking=True)
    email = fields.Char(string='البريد الإلكتروني', required=True, tracking=True)
    customer_type = fields.Selection([
        ('individual', 'فرد'),
        ('company', 'شركة / مؤسسة'),
        ('government', 'جهة حكومية'),
    ], string='نوع العميل', default='company', required=True, tracking=True)

    project_type = fields.Selection([
        ('commercial', 'مشروع تجاري / أبراج'),
        ('residential', 'مجمع سكني / فيلا'),
        ('industrial', 'مشروع صناعي / مستودعات'),
        ('infrastructure', 'بنية تحتية وكهروميكانيك'),
        ('renovation', 'ترميم وتطوير'),
    ], string='نوع المشروع', default='commercial', required=True, tracking=True)

    project_location = fields.Char(string='موقع المشروع (المدينة/الحي)', required=True, tracking=True)
    service_id = fields.Many2one('wasm.service', string='الخدمة المطلوبة')
    service_name = fields.Char(string='مسمى الخدمة المطلوبة')
    
    area = fields.Float(string='مساحة المشروع (م²)', help='المساحة الإجمالية للمشروع بالمتر المربع')
    approx_budget = fields.Float(string='الميزانية التقريبية (ريال سعودي)')
    expected_start_date = fields.Date(string='الموعد المتوقع لبدء المشروع')
    details = fields.Text(string='تفاصيل ومتطلبات المشروع')
    currency_id = fields.Many2one(
        'res.currency', string='العملة',
        default=lambda self: self.env.company.currency_id,
    )

    attachment_ids = fields.Many2many('ir.attachment', string='الملفات والمخططات المرفقة')
    attachment_count = fields.Integer(string='عدد المرفقات', compute='_compute_attachment_count')

    department = fields.Selection([
        ('engineering', 'قسم الهندسة والتصاميم'),
        ('sales', 'قسم المبيعات وطلبات عروض الأسعار'),
        ('projects', 'قسم إدارة المشاريع'),
        ('hr', 'قسم الموارد البشرية'),
        ('management', 'الإدارة العامة'),
    ], string='القسم المختص', default='sales', required=True, tracking=True)

    state = fields.Selection([
        ('new', 'جديد'),
        ('under_review', 'قيد المراجعة'),
        ('contacted', 'تم التواصل مع العميل'),
        ('pricing', 'قيد التسعير وحصر الكميات'),
        ('offer_sent', 'تم إرسال عرض السعر'),
        ('contracted', 'تم التعاقد'),
        ('closed', 'مغلق'),
    ], string='حالة الطلب', default='new', tracking=True, required=True)

    notes = fields.Text(string='ملاحظات سريعة / متابعة داخلية')
    source = fields.Selection([
        ('quote', 'طلب عرض سعر'),
        ('contact', 'رسالة من صفحة التواصل'),
    ], string='مصدر الطلب', default='quote', required=True, tracking=True,
        help='يحدد بداية الرقم المرجعي: RFQ لطلبات عروض الأسعار و MSG لرسائل صفحة التواصل')

    client_ip = fields.Char(string='عنوان IP للمرسل', readonly=True, copy=False, index=True,
                            help='يُستخدم للحد من الطلبات المتكررة من نفس الجهاز (حماية من الرسائل المزعجة)')

    _REF_TYPES = {'quote': 'RFQ', 'contact': 'MSG'}

    @api.model
    def wasm_recent_count_from_ip(self, ip, minutes=10):
        """Number of website requests sent from ``ip`` during the last ``minutes``."""
        if not ip:
            return 0
        since = fields.Datetime.now() - timedelta(minutes=minutes)
        return self.sudo().with_context(active_test=False).search_count(
            [('client_ip', '=', ip), ('create_date', '>=', since)])

    @api.model
    def _wasm_new_reference(self, source):
        """ARFA-RFQ-2610-0063: type (RFQ quote / MSG contact message), year+month, running number."""
        number = self.env['ir.sequence'].next_by_code('wasm.quote.request') or '0'
        number = ''.join(ch for ch in number if ch.isdigit()) or '0'
        return 'ARFA-%s-%s-%s' % (self._REF_TYPES.get(source, 'RFQ'),
                                  fields.Date.context_today(self).strftime('%y%m'), number.zfill(4))

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self._wasm_new_reference(vals.get('source') or 'quote')
            if not vals.get('access_token'):
                vals['access_token'] = str(uuid.uuid4())
        records = super().create(vals_list)
        # The website controller sends the notifications itself once the uploaded files are linked
        # (otherwise the e-mail would always say "0 attachments").
        if not self.env.context.get('wasm_defer_notifications'):
            records._wasm_notify()
        return records

    def _wasm_notify(self):
        for rec in self:
            try:
                rec.action_send_email_notifications()
            except Exception as e:
                _logger.error("Error triggering email notification for record %s: %s", rec.name, str(e))

    def action_send_email_notifications(self):
        """Send automatic emails to Target Admin & Customer with Unique Reference Number via Odoo Mail Server."""
        site_config = self.env['wasm.site.config'].sudo().get_config()
        if not site_config:
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='')

        for req in self:
            customer_type_dict = dict(self._fields['customer_type'].selection)
            project_type_dict = dict(self._fields['project_type'].selection)
            department_dict = dict(self._fields['department'].selection)

            cust_type_lbl = customer_type_dict.get(req.customer_type, req.customer_type or '')
            proj_type_lbl = project_type_dict.get(req.project_type, req.project_type or '')
            dept_lbl = department_dict.get(req.department, req.department or '')
            service_name = req.service_id.name if req.service_id else (req.service_name or 'طلب عام / استفسار')

            backend_link = f"{base_url}/web#id={req.id}&model=wasm.quote.request&view_type=form"
            # Values typed by website visitors are HTML-escaped before going into the e-mail
            # bodies (prevents HTML/link injection in mails sent from the company address).
            c_name = str(escape(req.customer_name or ''))
            c_email = str(escape(req.email or ''))
            c_phone = str(escape(req.phone or ''))
            c_location = str(escape(req.project_location or ''))
            service_html = str(escape(service_name or ''))

            # 1. Admin / Company Notification Email
            if site_config.enable_email_notifications and site_config.target_notification_email:
                admin_target_email = site_config.target_notification_email.strip()
                subject_name = ' '.join((req.customer_name or '').split())[:80]   # no CR/LF in headers
                admin_subject = f"[إشعار طلب جديد {req.name}] - {subject_name} ({proj_type_lbl})"
                
                admin_body_html = f"""
                <div style="font-family: 'Tajawal', 'Alexandria', Arial, sans-serif; direction: rtl; text-align: right; background-color: #f8fafc; padding: 25px; color: #1e293b;">
                    <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px 30px; text-align: center; border-bottom: 4px solid #d97706;">
                            <h2 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 800;">شركة عرفة للأنظمة المتخصصة</h2>
                            <p style="color: #f59e0b; margin: 5px 0 0 0; font-size: 14px; font-weight: 700;">إشعار تلقائي بطلب جديد عبر الموقع الإلكتروني</p>
                        </div>
                        <div style="background: #fff7ed; border-bottom: 1px solid #fed7aa; padding: 16px 30px; text-align: center;">
                            <span style="font-size: 13px; color: #9a3412; display: block; margin-bottom: 4px; font-weight: 700;">الرقم المرجعي المميز للطلب:</span>
                            <span style="font-size: 26px; font-weight: 900; color: #c2410c; letter-spacing: 1px;">{req.name}</span>
                        </div>
                        <div style="padding: 30px;">
                            <h3 style="color: #0f172a; font-size: 18px; margin-top: 0; border-bottom: 2px solid #f1f5f9; padding-bottom: 10px;">📋 تفاصيل الطلب وبيانات التواصل:</h3>
                            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569; width: 38%;">اسم العميل / الجهة:</td>
                                    <td style="padding: 10px; font-weight: 800; color: #0f172a;">{c_name} ({cust_type_lbl})</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">رقم الجوال:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a; direction: ltr; text-align: right;"><a href="tel:{c_phone}" style="color: #d97706; text-decoration: none;">{c_phone}</a></td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">البريد الإلكتروني:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;"><a href="mailto:{c_email}" style="color: #d97706; text-decoration: none;">{c_email}</a></td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">نوع المشروع:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{proj_type_lbl}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">موقع المشروع:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{c_location}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">الخدمة المطلوبة:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{service_html}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">القسم المختص:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{dept_lbl}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #f1f5f9;">
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">المساحة والميزانية:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{req.area or 0.0} م² | {req.approx_budget or 0.0} ريال سعودي</td>
                                </tr>
                                <tr>
                                    <td style="padding: 10px; font-weight: 700; color: #475569;">المرفقات والمخططات:</td>
                                    <td style="padding: 10px; font-weight: 700; color: #0f172a;">{req.attachment_count} ملف مرفق</td>
                                </tr>
                            </table>
                            <div style="background: #f8fafc; border-right: 4px solid #d97706; padding: 15px; border-radius: 8px; margin-bottom: 25px;">
                                <span style="font-weight: 800; color: #0f172a; display: block; margin-bottom: 6px;">📝 تفاصيل ومتطلبات المشروع:</span>
                                <p style="margin: 0; color: #334155; line-height: 1.6; white-space: pre-wrap;">{str(escape(req.details)) if req.details else 'لا توجد تفاصيل إضافية مكتوبة.'}</p>
                            </div>
                            <div style="text-align: center; margin-top: 30px;">
                                <a href="{backend_link}" target="_blank" style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: #ffffff; font-weight: 800; text-decoration: none; padding: 14px 32px; border-radius: 50px; display: inline-block; box-shadow: 0 4px 15px rgba(217,119,6,0.35);">
                                    🔗 فتح الطلب في نظام أودو Backend
                                </a>
                            </div>
                        </div>
                        <div style="background: #f1f5f9; padding: 16px 30px; text-align: center; font-size: 12px; color: #64748b;">
                            تم إرسال هذا الإشعار تلقائياً من نظام شركة عرفة للأنظمة المتخصصة.
                        </div>
                    </div>
                </div>
                """

                admin_mail_values = {
                    'subject': admin_subject,
                    'body_html': admin_body_html,
                    'email_to': admin_target_email,
                    'email_from': self.env.company.email or 'info@arfa-sa.com',
                    'auto_delete': False,
                }
                try:
                    self.env['mail.mail'].sudo().create(admin_mail_values)
                    # Removed .send() to allow async processing via Odoo mail queue
                    _logger.info("Admin notification email queued for %s to %s", req.name, admin_target_email)
                except Exception as e:
                    _logger.error("Failed to queue admin notification email for %s: %s", req.name, str(e))

            # 2. Customer Confirmation Email
            if site_config.enable_customer_confirmation_email and req.email:
                cust_subject = f"تأكيد استلام طلبكم برقم مرجعي: {req.name} - شركة عرفة للأنظمة المتخصصة"
                cust_body_html = f"""
                <div style="font-family: 'Tajawal', 'Alexandria', Arial, sans-serif; direction: rtl; text-align: right; background-color: #f8fafc; padding: 25px; color: #1e293b;">
                    <div style="max-width: 650px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.08); border: 1px solid #e2e8f0;">
                        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px 30px; text-align: center; border-bottom: 4px solid #d97706;">
                            <h2 style="color: #ffffff; margin: 0; font-size: 22px; font-weight: 800;">شركة عرفة للأنظمة المتخصصة</h2>
                            <p style="color: #f59e0b; margin: 5px 0 0 0; font-size: 14px; font-weight: 700;">شكراً لتواصلكم معنا</p>
                        </div>
                        <div style="padding: 30px;">
                            <h3 style="color: #0f172a; font-size: 18px; margin-top: 0;">عزيزنا {c_name}، المحترم</h3>
                            <p style="color: #475569; line-height: 1.7; font-size: 15px;">
                                نشكرك على التواصل مع <strong>شركة عرفة للأنظمة المتخصصة</strong>. نود إحاطتكم بأنه تم استلام طلبكم بنجاح وتحويله للقسم المختص للمراجعة ودراسة المتطلبات.
                            </p>
                            <div style="background: #fff7ed; border: 1px dashed #f97316; border-radius: 12px; padding: 20px; text-align: center; margin: 25px 0;">
                                <span style="font-size: 14px; color: #9a3412; display: block; margin-bottom: 5px; font-weight: 700;">الرقم المرجعي الخاص بطلبكم:</span>
                                <span style="font-size: 26px; font-weight: 900; color: #c2410c; letter-spacing: 1px;">{req.name}</span>
                                <span style="font-size: 12px; color: #7c2d12; display: block; margin-top: 6px;">يرجى الاحتفاظ بهذا الرقم لمتابعة حالة الطلب معنا</span>
                            </div>
                            <p style="color: #475569; line-height: 1.7; font-size: 15px;">
                                سيقوم أحد مهندسينا المختصين بالتواصل معكم عبر الجوال (<strong>{c_phone}</strong>) أو البريد خلال أوقات العمل الرسمية لمتابعة التفاصيل وتزويدكم بعرض السعر المعتمد.
                            </p>
                            <div style="border-top: 1px solid #f1f5f9; padding-top: 20px; margin-top: 30px;">
                                <p style="margin: 0; color: #0f172a; font-weight: 800; font-size: 14px;">مع خالص التحية والتقدير،</p>
                                <p style="margin: 4px 0 0 0; color: #d97706; font-weight: 700; font-size: 14px;">فريق عمل شركة عرفة للأنظمة المتخصصة</p>
                                <p style="margin: 4px 0 0 0; color: #64748b; font-size: 13px;">الرياض - المملكة العربية السعودية | هاتف: +966 11 234 5678</p>
                            </div>
                        </div>
                    </div>
                </div>
                """

                cust_mail_values = {
                    'subject': cust_subject,
                    'body_html': cust_body_html,
                    'email_to': req.email,
                    'email_from': self.env.company.email or 'info@arfa-sa.com',
                    'auto_delete': False,
                }
                try:
                    self.env['mail.mail'].sudo().create(cust_mail_values)
                    # Removed .send() to allow async processing via Odoo mail queue
                    _logger.info("Customer confirmation email queued for %s to %s", req.name, req.email)
                except Exception as e:
                    _logger.error("Failed to queue customer confirmation email for %s: %s", req.name, str(e))

    def action_under_review(self):
        return self.write({'state': 'under_review'})

    def action_contacted(self):
        return self.write({'state': 'contacted'})

    def action_pricing(self):
        return self.write({'state': 'pricing'})

    def action_offer_sent(self):
        return self.write({'state': 'offer_sent'})

    def action_contracted(self):
        return self.write({'state': 'contracted'})

    def action_closed(self):
        return self.write({'state': 'closed'})

