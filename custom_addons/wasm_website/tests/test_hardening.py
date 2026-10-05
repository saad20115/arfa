# -*- coding: utf-8 -*-
"""19.0.2.2.0 hardening: security grants, form token, URL fields, SEO meta, images."""
import base64
import io
import time

from PIL import Image

from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Command
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.wasm_website.content_setup import wasm_security_hardening
from odoo.addons.wasm_website.controllers.main import _clean_text
from odoo.addons.wasm_website.models.wasm_mixins import wasm_optimize_image_bytes, wasm_url_is_safe


def _png(width, height, alpha=False, noise=True):
    mode = 'RGBA' if alpha else 'RGB'
    if noise:
        image = Image.frombytes('RGB', (width, height), bytes((i * 7919) % 251 for i in range(width * height * 3)))
        image = image.convert(mode)
    else:
        image = Image.new(mode, (width, height), (200, 30, 30, 255) if alpha else (200, 30, 30))
    if alpha:
        image.putpixel((0, 0), (0, 0, 0, 0))
    buf = io.BytesIO()
    image.save(buf, 'PNG')
    return buf.getvalue()


@tagged('post_install', '-at_install')
class TestWasmSecurityHardening(TransactionCase):

    def test_hardening_removes_public_and_portal_grants(self):
        g_user = self.env.ref('wasm_website.group_wasm_user')
        g_manager = self.env.ref('wasm_website.group_wasm_manager')
        public = self.env.ref('base.public_user').with_context(active_test=False)
        portal_tpl = self.env.ref('base.template_portal_user_id').with_context(active_test=False)
        # reproduce the production state
        g_manager.write({'implied_ids': [Command.link(self.env.ref('base.group_system').id)]})
        self.env.cr.execute("INSERT INTO res_groups_users_rel (gid, uid) VALUES (%s, %s), (%s, %s), (%s, %s), (%s, %s)"
                            " ON CONFLICT DO NOTHING",
                            (g_user.id, public.id, g_manager.id, public.id,
                             g_user.id, portal_tpl.id, g_manager.id, portal_tpl.id))
        self.env.invalidate_all()
        self.env['ir.config_parameter'].set_param('auth_signup.invitation_scope', 'b2c')

        changes = wasm_security_hardening(self.env)
        self.assertTrue(changes)
        self.env.invalidate_all()
        self.assertEqual(g_manager.implied_ids, g_user)
        self.assertEqual(g_user.implied_ids, self.env.ref('base.group_user'))
        self.assertEqual(public.group_ids, self.env.ref('base.group_public'))
        self.assertEqual(portal_tpl.group_ids, self.env.ref('base.group_portal'))
        self.assertTrue(public.share)
        self.assertTrue(portal_tpl.share)
        self.assertFalse(public.has_group('base.group_system'))
        self.assertEqual(self.env['ir.config_parameter'].get_param('auth_signup.invitation_scope'), 'b2b')
        # idempotent
        self.assertFalse(wasm_security_hardening(self.env))

    def test_public_user_cannot_read_quote_attachment(self):
        quote = self.env['wasm.quote.request'].create({
            'customer_name': 'A', 'phone': '0501234567', 'email': 'a@example.com', 'project_location': 'Riyadh'})
        attachment = self.env['ir.attachment'].create({
            'name': 'boq.pdf', 'datas': base64.b64encode(b'%PDF-1.4 secret'),
            'res_model': 'wasm.quote.request', 'res_id': quote.id})
        public = self.env.ref('base.public_user')
        with self.assertRaises(AccessError):
            attachment.with_user(public).check_access('read')
        with self.assertRaises(AccessError):
            quote.with_user(public).check_access('read')

    def test_wasm_user_cannot_delete_quotes(self):
        user = self.env['res.users'].create({
            'name': 'Quote clerk', 'login': 'quote_clerk_test',
            'group_ids': [Command.set([self.env.ref('wasm_website.group_wasm_user').id])]})
        quote = self.env['wasm.quote.request'].create({
            'customer_name': 'A', 'phone': '0501234567', 'email': 'a@example.com', 'project_location': 'Riyadh'})
        quote.with_user(user).write({'notes': 'called'})
        with self.assertRaises(AccessError):
            quote.with_user(user).unlink()
        self.assertFalse(user.has_group('base.group_system'))


@tagged('post_install', '-at_install')
class TestWasmFormToken(TransactionCase):

    def setUp(self):
        super().setUp()
        self.Config = self.env['wasm.site.config']

    def _token(self, age):
        ts = int(time.time()) - age
        return '%s.%s' % (ts, self.Config._wasm_form_signature(ts))

    def test_token_format_and_validity(self):
        token = self.Config.wasm_form_token()
        ts, sig = token.split('.')
        self.assertTrue(ts.isdigit())
        self.assertEqual(len(sig), 32)
        self.assertFalse(self.Config.wasm_check_form_token(token), 'a fresh token is younger than 3 s')
        self.assertTrue(self.Config.wasm_check_form_token(token, now=int(ts) + 5))
        self.assertTrue(self.Config.wasm_check_form_token(self._token(10)))
        self.assertTrue(self.Config.wasm_check_form_token(self._token(23 * 3600)))

    def test_token_rejected(self):
        check = self.Config.wasm_check_form_token
        self.assertFalse(check(self._token(25 * 3600)), 'older than 24 h')
        self.assertFalse(check(self._token(-60)), 'from the future')
        ts = int(time.time()) - 10
        self.assertFalse(check('%s.%s' % (ts, '0' * 32)), 'forged signature')
        self.assertFalse(check('%s.%s' % (ts + 1, self.Config._wasm_form_signature(ts))), 'timestamp changed')
        for value in (None, '', 'abc', str(ts), '%s.' % ts, '1.2.3', str(int(time.time() * 1000)), 'x' * 100, 12345):
            self.assertFalse(check(value), value)


@tagged('post_install', '-at_install')
class TestWasmCleaning(TransactionCase):

    def test_clean_text(self):
        self.assertEqual(_clean_text('Evil\r\nBcc: x@y.com\x00 ', single_line=True), 'Evil Bcc: x@y.com')
        self.assertEqual(_clean_text(' a \t  b\x7f ', single_line=True), 'a b')
        self.assertEqual(_clean_text('line1\r\nline2\x00\x1b[31m', single_line=False), 'line1\nline2[31m')
        self.assertEqual(_clean_text(None), '')
        self.assertEqual(_clean_text(['list']), '')

    def test_phone_e164(self):
        e164 = self.env['wasm.site.config'].wasm_phone_e164
        self.assertEqual(e164('+966 0545432343'), '+966545432343')
        self.assertEqual(e164('0545432343'), '+966545432343')
        self.assertEqual(e164('00966 54 543 2343'), '+966545432343')
        self.assertEqual(e164('+966 11 234 5678'), '+966112345678')
        self.assertEqual(e164(''), '')


@tagged('post_install', '-at_install')
class TestWasmUrlFields(TransactionCase):

    def test_url_helper(self):
        for ok in ('https://arfa-sa.com', 'http://x.y/a?b=1', '/about', '/wasm_website/static/x.mp4', '', False):
            self.assertTrue(wasm_url_is_safe(ok), ok)
        for bad in ('javascript:alert(1)', '//evil.com', '/\\evil.com', 'data:text/html,x', 'www.x.com',
                    'https://', 'https://a b', 'vbscript:x', 'https://x\n.com'):
            self.assertFalse(wasm_url_is_safe(bad), bad)
        self.assertTrue(wasm_url_is_safe('{whatsapp}', extra_link=True))
        self.assertTrue(wasm_url_is_safe('tel:+966545432343', extra_link=True))
        self.assertTrue(wasm_url_is_safe('mailto:info@arfa-sa.com', extra_link=True))
        self.assertFalse(wasm_url_is_safe('javascript:x', extra_link=True))

    def test_constraints(self):
        project = self.env['wasm.project'].create({'name': 'P', 'location': 'Riyadh'})
        with self.assertRaises(ValidationError):
            project.video_url = 'javascript:alert(1)'
        project.video_url = 'https://www.youtube.com/watch?v=abcdefgh'
        partner = self.env['wasm.partner'].create({'name': 'X', 'website_url': 'https://x.sa'})
        with self.assertRaises(ValidationError):
            partner.website_url = '//evil.com'
        with self.assertRaises(ValidationError):
            self.env['wasm.content.item'].create({'section': 'pillar', 'link_url': 'javascript:void(0)'})
        self.env['wasm.content.item'].create({'section': 'footer_link', 'link_url': '{whatsapp}'})
        with self.assertRaises(ValidationError):
            self.env['wasm.news'].create({'name': 'N', 'image_url': 'data:image/png;base64,AAAA'})
        config = self.env['wasm.site.config'].get_config()
        with self.assertRaises(ValidationError):
            config.social_x = 'javascript:alert(1)'
        with self.assertRaises(ValidationError):
            config.map_embed_url = 'https://evil.example/maps/embed'
        config.map_embed_url = 'https://www.google.com/maps/embed?pb=!1m18'
        config.social_linkedin = 'https://www.linkedin.com/company/arfa'


@tagged('post_install', '-at_install')
class TestWasmSeoMeta(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].set_param('web.base.url', 'https://arfa-sa.com')
        cls.config = cls.env['wasm.site.config'].get_config()
        cls.project = cls.env['wasm.project'].create({
            'name': 'Leaky Project Name', 'location': 'Riyadh', 'description': 'word ' * 80,
            'image': base64.b64encode(_png(64, 48, noise=False))})

    def test_project_does_not_leak_on_home(self):
        meta = self.config.wasm_page_meta('/', True, project=self.project)
        self.assertNotEqual(meta['name'], self.project.name)
        self.assertNotIn(self.project.name, meta['title'] or '')
        self.assertIsNone(meta['image'])
        meta = self.config.wasm_page_meta('/projects', True, project=self.project)
        self.assertNotIn(self.project.name, meta['title'] or '')

    def test_project_page_meta(self):
        meta = self.config.wasm_page_meta('/projects/%s' % self.project.id, True, project=self.project)
        self.assertEqual(meta['name'], self.project.name)
        self.assertTrue(meta['image'].startswith('https://arfa-sa.com/wasm/project/%s/image' % self.project.id))
        self.assertLessEqual(len(meta['description']), 155)
        self.assertTrue(meta['description'].endswith('…'))

    def test_service_and_news_guard(self):
        service = self.env['wasm.service'].create({'name': 'Guard Service', 'slug': 'guard-service'})
        meta = self.config.wasm_page_meta('/services/guard-service', True, service=service)
        self.assertEqual(meta['name'], service.wasm_title())
        meta = self.config.wasm_page_meta('/services', True, service=service)
        self.assertNotEqual(meta['name'], service.wasm_title())
        article = self.env['wasm.news'].create({'name': 'Guard News', 'title_en': 'Guard News'})
        self.assertNotEqual(self.config.wasm_page_meta('/news', True, article=article)['name'], 'Guard News')
        self.assertEqual(self.config.wasm_page_meta('/news/%s' % article.id, True, article=article)['name'], 'Guard News')

    def test_social_meta_and_base_url(self):
        meta = {'opengraph_meta': {'og:url': 'http://evil.example/projects', 'og:image': '/web/image/website/1/logo'},
                'twitter_meta': {'twitter:image': 'http://evil.example/web/image/x'}}
        self.config.wasm_patch_social_meta(meta, 'T', 'D', True, 'http://evil.example/')
        self.assertEqual(meta['opengraph_meta']['og:url'], 'https://arfa-sa.com/projects')
        self.assertEqual(meta['opengraph_meta']['og:image'], 'https://arfa-sa.com/web/image/website/1/logo')
        self.assertEqual(meta['twitter_meta']['twitter:image'], 'https://arfa-sa.com/web/image/x')
        self.config.wasm_patch_social_meta(meta, 'T', 'D', True, 'http://evil.example/', image='https://arfa-sa.com/i.jpg')
        self.assertEqual(meta['opengraph_meta']['og:image'], 'https://arfa-sa.com/i.jpg')
        self.assertEqual(meta['twitter_meta']['twitter:image'], 'https://arfa-sa.com/i.jpg')
        jsonld = str(self.config.wasm_jsonld('http://evil.example/'))
        self.assertIn('https://arfa-sa.com/#organization', jsonld)
        self.assertNotIn('evil.example', jsonld)
        self.assertNotIn('evil.example', self.config.wasm_llms_text('http://evil.example/'))
        self.env['wasm.news'].create({'name': 'LLMS article', 'title_en': 'LLMS article'})
        llms = self.config.wasm_llms_text()
        self.assertIn('## News', llms)
        self.assertIn('LLMS article](https://arfa-sa.com/news/', llms)

    def test_hide_from_search_switch(self):
        ICP = self.env['ir.config_parameter']
        for value, expected in (('True', True), ('1', True), ('true', True), ('False', False), ('', False)):
            ICP.set_param('wasm_website.hide_from_search_engines', value)
            self.assertEqual(self.config.wasm_hide_from_search(), expected, value)
        self.config.hide_from_search_engines = True
        self.assertEqual(ICP.get_param('wasm_website.hide_from_search_engines'), 'True')
        self.config.hide_from_search_engines = False
        self.assertFalse(self.config.wasm_hide_from_search())


@tagged('post_install', '-at_install')
class TestWasmImageOptimizer(TransactionCase):

    def test_large_image_is_resized_and_recompressed(self):
        raw = _png(2400, 1600)
        item = self.env['wasm.content.item'].create({'section': 'pillar', 'image': base64.b64encode(raw)})
        stored = base64.b64decode(item.with_context(bin_size=False).image)
        image = Image.open(io.BytesIO(stored))
        self.assertEqual(image.format, 'JPEG')
        self.assertLessEqual(max(image.size), 800)
        self.assertLess(len(stored), len(raw))

    def test_transparent_png_stays_png(self):
        out = wasm_optimize_image_bytes(_png(3000, 1000, alpha=True), 1920)
        image = Image.open(io.BytesIO(out))
        self.assertEqual(image.format, 'PNG')
        self.assertEqual(max(image.size), 1920)

    def test_small_image_untouched_and_svg_skipped(self):
        small = _png(300, 200, noise=False)
        self.assertIs(wasm_optimize_image_bytes(small, 1200), small)
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>'
        self.assertIs(wasm_optimize_image_bytes(svg, 10), svg)

    def test_existing_images_optimizer(self):
        raw = _png(1500, 1500)      # within the field's own 1600 px limit, above the 800 px card size
        item = self.env['wasm.content.item'].with_context(wasm_skip_image_optimize=True).create(
            {'section': 'why', 'image': base64.b64encode(raw)})
        self.assertEqual(len(base64.b64decode(item.with_context(bin_size=False).image)), len(raw))
        self.assertEqual(item._wasm_optimize_existing_images(), 1)
        stored = base64.b64decode(item.with_context(bin_size=False).image)
        self.assertLessEqual(max(Image.open(io.BytesIO(stored)).size), 800)
