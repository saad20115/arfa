# -*- coding: utf-8 -*-
"""Website controllers: anti-spam, input cleaning, uploads, public routes (19.0.2.2.0)."""
import base64
import time
from datetime import timedelta

from odoo import fields, http
from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestWasmPublicForms(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Quote = cls.env['wasm.quote.request']
        cls.config = cls.env['wasm.site.config'].get_config()
        cls.config.write({'enable_email_notifications': True, 'target_notification_email': 'sales@example.com'})
        cls.service = cls.env['wasm.service'].create({'name': 'Form Service', 'slug': 'form-service'})
        cls.archived_service = cls.env['wasm.service'].create({'name': 'Old Service', 'slug': 'old-service',
                                                               'active': False})

    def setUp(self):
        super().setUp()
        self.authenticate(None, None)

    def _token(self, age=10):
        ts = int(time.time()) - age
        return '%s.%s' % (ts, self.env['wasm.site.config']._wasm_form_signature(ts))

    def _post(self, url='/quote/submit', files=None, **values):
        data = {
            'customer_name': 'Test Customer', 'phone': '0501234567', 'email': 'client@example.com',
            'project_location': 'Riyadh', 'details': 'Need a quote', 'form_ts': self._token(),
            'csrf_token': http.Request.csrf_token(self),
        }
        data.update(values)
        data = {k: v for k, v in data.items() if v is not None}
        return self.url_open(url, data=data, files=files, allow_redirects=False)

    def _last_quote(self):
        return self.Quote.search([], order='id desc', limit=1)

    # --- anti-bot token -------------------------------------------------------
    def test_valid_submission(self):
        count = self.Quote.search_count([])
        response = self._post()
        self.assertEqual(response.status_code, 303, response.text[:300])
        self.assertIn('/quote/thanks?token=', response.headers['Location'])
        self.assertEqual(self.Quote.search_count([]), count + 1)
        self.assertEqual(self._last_quote().client_ip, '127.0.0.1')

    def test_token_required(self):
        count = self.Quote.search_count([])
        for token in (None, '', str(int(time.time() * 1000)), self._token(age=0), self._token(age=90000),
                      '%s.%s' % (int(time.time()) - 10, 'f' * 32)):
            response = self._post(form_ts=token)
            self.assertIn('error=invalid', response.headers.get('Location', ''), token)
        response = self._post(url='/contactus/submit', form_ts=None)
        self.assertIn('/contactus?error=invalid', response.headers.get('Location', ''))
        self.assertEqual(self.Quote.search_count([]), count)

    def test_honeypot(self):
        response = self._post(website_url='http://spam.example')
        self.assertIn('error=invalid', response.headers.get('Location', ''))

    # --- rate limit by IP (database) ------------------------------------------
    def test_rate_limit_by_ip(self):
        vals = {'customer_name': 'x', 'phone': '0501234567', 'email': 'x@example.com', 'project_location': 'x'}
        old = self.Quote.create([dict(vals, client_ip='127.0.0.1') for _i in range(5)])
        self.env.cr.execute("UPDATE wasm_quote_request SET create_date = %s WHERE id IN %s",
                            (fields.Datetime.now() - timedelta(minutes=11), tuple(old.ids)))
        self.assertEqual(self.Quote.wasm_recent_count_from_ip('127.0.0.1'), 0, 'older than 10 minutes')
        self.Quote.create([dict(vals, client_ip='10.9.9.9') for _i in range(5)])
        self.assertEqual(self.Quote.wasm_recent_count_from_ip('10.9.9.9'), 5)
        for _i in range(5):
            self.assertIn('/quote/thanks', self._post().headers['Location'])
        count = self.Quote.search_count([])
        response = self._post()
        self.assertIn('error=rate_limit', response.headers['Location'])
        response = self._post(url='/contactus/submit')
        self.assertIn('/contactus?error=rate_limit', response.headers['Location'])
        self.assertEqual(self.Quote.search_count([]), count)

    # --- input cleaning ---------------------------------------------------------
    def test_input_cleaning(self):
        response = self._post(customer_name='Evil\r\nBcc: victim@example.com\x00',
                              project_location='  Riyadh\t\n  North ', details='line 1\r\nline 2\x00\x07')
        self.assertIn('/quote/thanks', response.headers['Location'])
        quote = self._last_quote()
        self.assertEqual(quote.customer_name, 'Evil Bcc: victim@example.com')
        self.assertEqual(quote.project_location, 'Riyadh North')
        self.assertEqual(quote.details, 'line 1\nline 2')
        mails = self.env['mail.mail'].search([('subject', 'ilike', quote.name)])
        self.assertTrue(mails)
        for mail in mails:
            self.assertNotIn('\n', mail.subject)
            self.assertNotIn('\r', mail.subject)

    def test_service_id_validation(self):
        for value, expected in (('99999999999999999999', False), ('99999999', False), ('²', False),
                                ('-1', False), (str(self.archived_service.id), False),
                                (str(self.service.id), self.service)):
            self.env.cr.execute("UPDATE wasm_quote_request SET client_ip = NULL")   # stay under the rate limit
            response = self._post(service_id=value)
            self.assertEqual(response.status_code, 303, value)
            self.assertIn('/quote/thanks', response.headers['Location'], value)
            self.assertEqual(self._last_quote().service_id, expected or self.env['wasm.service'], value)
        self.assertEqual(self.url_open('/quote?service_id=99999999999999999999').status_code, 200)
        self.assertEqual(self.url_open('/quote?service_id=%C2%B2').status_code, 200)

    def test_notification_counts_attachments(self):
        files = {'attachments': ('boq.pdf', b'%PDF-1.4 test file', 'application/pdf')}
        response = self._post(files=files)
        self.assertIn('/quote/thanks', response.headers['Location'])
        quote = self._last_quote()
        self.assertEqual(quote.attachment_count, 1)
        admin_mail = self.env['mail.mail'].search([('subject', 'ilike', quote.name),
                                                   ('email_to', '=', 'sales@example.com')])
        self.assertEqual(len(admin_mail), 1)
        self.assertIn('1 ملف مرفق', admin_mail.body_html)

    # --- public access ----------------------------------------------------------
    def test_public_cannot_download_quote_attachment(self):
        quote = self.Quote.create({'customer_name': 'x', 'phone': '0501234567', 'email': 'x@example.com',
                                   'project_location': 'x'})
        attachment = self.env['ir.attachment'].create({
            'name': 'secret.pdf', 'datas': base64.b64encode(b'%PDF-1.4 very secret'),
            'res_model': 'wasm.quote.request', 'res_id': quote.id})
        response = self.url_open('/web/content/%s?download=true' % attachment.id, allow_redirects=False)
        self.assertIn(response.status_code, (403, 404))
        self.assertNotIn(b'very secret', response.content)

    def test_website_info_hidden(self):
        self.assertEqual(self.url_open('/website/info').status_code, 404)

    def test_archived_images_not_served(self):
        image = b'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
        active = self.env['wasm.testimonial'].create({'name': 'A', 'feedback': 'ok', 'image': image})
        archived = self.env['wasm.testimonial'].create({'name': 'B', 'feedback': 'ok', 'image': image,
                                                        'active': False})
        self.assertTrue(active.wasm_image_url().startswith('/wasm/testimonial/%s/image?unique=' % active.id))
        self.assertEqual(self.env['wasm.testimonial'].create({'name': 'C', 'feedback': 'x'}).wasm_image_url(), '')
        self.assertEqual(self.url_open(active.wasm_image_url()).status_code, 200)
        self.assertEqual(self.url_open('/wasm/testimonial/%s/image' % archived.id).status_code, 404)
        project = self.env['wasm.project'].create({'name': 'Hidden', 'location': 'x', 'image': image,
                                                   'active': False})
        self.assertEqual(self.url_open('/wasm/project/%s/image' % project.id, allow_redirects=False).status_code, 404)

    def test_robots_txt(self):
        ICP = self.env['ir.config_parameter']
        ICP.set_param('web.base.url', 'https://arfa-sa.com')
        ICP.set_param('wasm_website.hide_from_search_engines', 'False')
        text = self.url_open('/robots.txt').text     # (forged Host headers: see TestWasmSeoMeta)
        self.assertIn('Sitemap: https://arfa-sa.com/sitemap.xml', text)
        self.assertIn('Disallow: /web', text)
        ICP.set_param('wasm_website.hide_from_search_engines', 'True')
        self.assertEqual(self.url_open('/robots.txt').text, 'User-agent: *\nDisallow: /\n')
