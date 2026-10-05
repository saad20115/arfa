# -*- coding: utf-8 -*-
import base64
import logging
import math
import os
import re

from werkzeug.exceptions import NotFound

from odoo import http
from odoo.http import request
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.website.controllers.main import Website
from odoo.addons.wasm_website.models.wasm_site_config import DEFAULT_IMAGES
from odoo.addons.wasm_website.models.wasm_service import LEGACY_SLUGS

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

# --- Anti-spam / validation ---------------------------------------------------
EMAIL_RE = re.compile(r'^[^@\s<>"\']{1,64}@[^@\s<>"\']{1,190}\.[A-Za-z]{2,24}$')
PHONE_RE = re.compile(r'^[0-9+()\-\s]{7,20}$')
FIELD_LIMITS = {'customer_name': 120, 'phone': 20, 'email': 254, 'project_location': 150, 'details': 5000}
SINGLE_LINE_FIELDS = ('customer_name', 'phone', 'email', 'project_location')
RATE_LIMIT_MINUTES = 10      # window of the per-IP limit (stored in wasm.quote.request.client_ip)
RATE_LIMIT_MAX = 5           # submissions per IP per window
BLOCKED_MIMETYPES = ('text/html', 'application/x-msdownload', 'application/x-sh', 'application/javascript',
                     'image/svg+xml', 'application/x-dosexec', 'application/x-executable')
# C0/C1 control characters except TAB / LF (CR is normalised first), plus bidi overrides
_CONTROL_RE = re.compile('[\x00-\x08\x0b-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]')
_SERVICE_ID_RE = re.compile(r'^[0-9]{1,9}$')


def _client_ip():
    """Visitor IP. Behind nginx Odoo rewrites remote_addr from X-Forwarded-For (proxy_mode)."""
    return (request.httprequest.remote_addr or '')[:64]


def _wasm_spam_reason(post):
    """Return a short reason string when the submission looks automated, else None."""
    # honeypot: hidden field real visitors never fill
    if (post.get('website_url') or '').strip():
        return 'honeypot'
    # signed timestamp rendered in the form: missing / forged / too fast / too old
    config = request.env['wasm.site.config'].sudo()
    if not config.wasm_check_form_token(post.get('form_ts')):
        return 'token'
    # per-IP rate limit, counted in the database (shared by all workers and servers)
    if request.env['wasm.quote.request'].sudo().wasm_recent_count_from_ip(
            _client_ip(), RATE_LIMIT_MINUTES) >= RATE_LIMIT_MAX:
        return 'rate_limit'
    return None


_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '01234567890123456789')


def _clean_text(value, single_line=False):
    """Visitor text without control characters; single-line values get collapsed whitespace."""
    value = value if isinstance(value, str) else ''
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    if single_line:
        value = ' '.join(_CONTROL_RE.sub(' ', value).split())
    else:
        value = _CONTROL_RE.sub('', value).strip()
    return value


def _clean(post, key):
    value = _clean_text(post.get(key), single_line=key in SINGLE_LINE_FIELDS)
    if key == 'phone':
        value = value.translate(_DIGITS)       # accept Arabic-Indic digits
    limit = FIELD_LIMITS.get(key)
    return value[:limit] if limit else value


def _parse_service_id(value):
    """Id of an active wasm.service, or False (rejects huge / unknown / archived ids)."""
    value = value.strip() if isinstance(value, str) else ''
    if not _SERVICE_ID_RE.match(value):
        return False
    service = request.env['wasm.service'].sudo().browse(int(value)).exists()
    return service.id if service and service.active else False


def _parse_amount(value, upper):
    try:
        number = float(value or 0.0)
    except (ValueError, TypeError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return max(0.0, min(number, upper))


def _valid_contact(email, phone):
    return bool(EMAIL_RE.match(email)) and bool(PHONE_RE.match(phone))


def _parse_date(value):
    try:
        from datetime import date
        return date.fromisoformat(value).isoformat() if value else False
    except (ValueError, TypeError):
        return False


# --- SEO: sitemap entries for detail pages, 301 redirects for duplicate URLs ---
def _sitemap_projects(env, rule, qs):
    for project in env['wasm.project'].sudo().search([('active', '=', True)]):
        loc = '/projects/%s' % project.id
        if not qs or qs.lower() in loc:
            entry = {'loc': loc}
            if project.write_date:
                entry['lastmod'] = project.write_date.date()
            yield entry


def _sitemap_news(env, rule, qs):
    for article in env['wasm.news'].sudo().search([('active', '=', True)]):
        loc = '/news/%s' % article.id
        if not qs or qs.lower() in loc:
            entry = {'loc': loc}
            if article.write_date:
                entry['lastmod'] = article.write_date.date()
            yield entry


def _sitemap_services(env, rule, qs):
    for service in env['wasm.service'].sudo().search([('active', '=', True), ('slug', '!=', False)],
                                                     order='sequence, id'):
        loc = service.website_url
        if not qs or qs.lower() in loc:
            entry = {'loc': loc}
            if service.write_date:
                entry['lastmod'] = service.write_date.date()
            yield entry


SEO_REDIRECTS = {
    '/about-us': '/about',
    '/our-group': '/our-company',
    '/group-companies': '/our-company',
    '/our-services': '/services',
    '/our-projects': '/projects',
    '/contact': '/contactus',
    '/contact-us': '/contactus',
    '/our-news': '/news',
    '/blog': '/news',
    '/blog/2': '/news',
}


class WasmWebsiteController(http.Controller):

    @http.route('/', type='http', auth='public', website=True)
    def wasm_home(self, **kw):
        site_config = request.env['wasm.site.config'].sudo().get_config()
        home_limit = site_config.home_projects_limit if site_config.home_projects_limit > 0 else 6
        values = {
            'site_config': site_config,
            'projects': request.env['wasm.project'].sudo().search(
                [('active', '=', True)], limit=home_limit, order='sequence, id desc'),
            'partners': request.env['wasm.partner'].sudo().search([('active', '=', True)], order='sequence, id'),
            'testimonials': request.env['wasm.testimonial'].sudo().search([('active', '=', True)], order='sequence, id'),
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
        record = record.exists() if record else record
        if record and 'active' in record._fields and not record.active:
            raise request.not_found()          # archived content is not public any more
        if record and record[field_name]:
            unique = bool(request.params.get('unique'))
            binary = request.env['ir.binary']
            if default_mimetype.startswith('image/') and not mimetype:
                stream = binary._get_image_stream_from(record, field_name, filename=filename)
            else:
                stream = binary._get_stream_from(record, field_name, filename=filename,
                                                 mimetype=mimetype, default_mimetype=default_mimetype)
            return stream.get_response(as_attachment=as_attachment, immutable=unique)
        if fallback_url:
            return request.redirect(fallback_url, local=fallback_url.startswith('/'))
        raise request.not_found()

    @http.route('/wasm/config/image/<string:field_name>', type='http', auth='public')
    def wasm_config_image(self, field_name, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        field = config._fields.get(field_name)
        if not field or field.type != 'binary' or field_name not in DEFAULT_IMAGES:
            raise request.not_found()
        return self._wasm_stream(config, field_name, fallback_url=DEFAULT_IMAGES.get(field_name) or None)

    @http.route('/wasm/partner/<int:partner_id>/logo', type='http', auth='public')
    def wasm_partner_logo_stream(self, partner_id, **kw):
        partner = request.env['wasm.partner'].sudo().browse(partner_id).exists()
        if partner and partner.active and not partner.logo and partner.logo_url:
            return request.redirect(partner.logo_url, local=False)
        return self._wasm_stream(partner, 'logo')

    @http.route('/wasm/project/<int:project_id>/image', type='http', auth='public')
    def wasm_project_image_stream(self, project_id, **kw):
        project = request.env['wasm.project'].sudo().browse(project_id)
        return self._wasm_stream(project, 'image', fallback_url='/wasm_website/static/src/img/project_conference_ritz.jpg')

    @http.route('/wasm/service/<int:service_id>/image', type='http', auth='public')
    def wasm_service_card_image_stream(self, service_id, **kw):
        service = request.env['wasm.service'].sudo().browse(service_id)
        return self._wasm_stream(service, 'image',
                                 fallback_url='/wasm_website/static/src/img/arfa_exhibition_building.webp')

    @http.route('/wasm/service/<int:service_id>/banner', type='http', auth='public')
    def wasm_service_banner_stream(self, service_id, **kw):
        service = request.env['wasm.service'].sudo().browse(service_id)
        return self._wasm_stream(service, 'banner_image', fallback_url='/wasm/service/%s/image' % service_id)

    @http.route('/wasm/item/<int:item_id>/image', type='http', auth='public')
    def wasm_content_item_image(self, item_id, **kw):
        item = request.env['wasm.content.item'].sudo().browse(item_id).exists()
        if item and item.active and not item.image and item.image_url:
            return request.redirect(item.image_url, local=item.image_url.startswith('/'))
        return self._wasm_stream(item, 'image')

    @http.route('/wasm/testimonial/<int:tid>/image', type='http', auth='public')
    def wasm_testimonial_image(self, tid, **kw):
        testimonial = request.env['wasm.testimonial'].sudo().browse(tid)
        return self._wasm_stream(testimonial, 'image')

    @http.route('/wasm/gallery/<int:media_id>/video', type='http', auth='public')
    def wasm_gallery_video_stream(self, media_id, **kw):
        media = request.env['wasm.gallery.image'].sudo().browse(media_id)
        return self._wasm_stream(media, 'video_file', mimetype='video/mp4', default_mimetype='video/mp4',
                                 filename=media.video_filename or 'video.mp4')

    @http.route('/wasm/video/hero', type='http', auth='public')
    def wasm_hero_video_stream(self, **kw):
        config = request.env['wasm.site.config'].sudo().get_config()
        return self._wasm_stream(config, 'home_hero_video_file',
                                 fallback_url=config.home_hero_video_url or '/wasm_website/static/src/video/hero_construction.mp4',
                                 mimetype='video/mp4', default_mimetype='video/mp4',
                                 filename=config.home_hero_video_filename or 'hero.mp4')

    # --- Service pages: legacy root URLs + /services/<slug> for services added later ---
    @http.route(['/%s' % slug for slug in LEGACY_SLUGS] + ['/services/<string:slug>'],
                type='http', auth='public', website=True, sitemap=_sitemap_services)
    def wasm_service_tab_page(self, slug=None, **kw):
        slug = slug or request.httprequest.path.strip('/').split('/')[-1]
        Service = request.env['wasm.service'].sudo()
        service = Service.search([('slug', '=', slug), ('active', '=', True)], limit=1)
        if not service:
            return request.redirect('/services')
        values = {
            'service': service,
            'other_services': Service.search([('active', '=', True), ('id', '!=', service.id)], order='sequence, id'),
            'site_config': request.env['wasm.site.config'].sudo().get_config(),
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

    @http.route('/about', type='http', auth='public', website=True)
    def wasm_about(self, **kw):
        return request.render('wasm_website.about_page_template', {
            'site_config': request.env['wasm.site.config'].sudo().get_config()})

    @http.route('/our-company', type='http', auth='public', website=True)
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

    @http.route('/services', type='http', auth='public', website=True)
    def wasm_services(self, **kw):
        services = request.env['wasm.service'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        return request.render('wasm_website.services_page_template', {'services': services})

    @http.route('/projects', type='http', auth='public', website=True)
    def wasm_projects(self, state=None, **kw):
        domain = [('active', '=', True)]
        if state in ('completed', 'in_progress'):
            domain.append(('state', '=', state))
        site_config = request.env['wasm.site.config'].sudo().get_config()
        page_limit = site_config.projects_page_limit if site_config and site_config.projects_page_limit > 0 else False
        projects = request.env['wasm.project'].sudo().search(domain, limit=page_limit, order='sequence, id desc')
        
        gallery = request.env['wasm.gallery.image'].sudo().search(
            [('active', '=', True), ('show_in_gallery', '=', True), ('service_id', '=', False)], order='sequence, id')
        values = {
            'projects': projects,
            'current_state': state or 'all',
            'site_config': site_config,
            'gallery': gallery,
        }
        return request.render('wasm_website.projects_page_template', values)

    @http.route('/projects/<int:project_id>', type='http', auth='public', website=True, sitemap=_sitemap_projects)
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
            'extra_gallery': self._wasm_extra_gallery(exclude_project=project),
            'site_config': request.env['wasm.site.config'].sudo().get_config(),
        }
        return request.render('wasm_website.project_detail_page_template', values)

    def _wasm_extra_gallery(self, exclude_project=None, limit=12):
        """Photos from the media gallery (other projects / general), with a static fallback."""
        domain = [('active', '=', True), ('show_in_gallery', '=', True), ('service_id', '=', False)]
        if exclude_project:
            domain += ['|', ('project_id', '=', False), ('project_id', '!=', exclude_project.id)]
        records = request.env['wasm.gallery.image'].sudo().search(domain, order='sequence, id desc', limit=limit)
        items = [{
            'media': rec,
            'url': rec.wasm_image_url(),
            'caption': rec.name or '',
            'project': rec.project_id.name or '',
            'project_url': rec.project_id and '/projects/%s' % rec.project_id.id or '',
        } for rec in records]
        return items

    @http.route('/wasm/project/<int:project_id>/media/<int:attachment_id>', type='http', auth='public')
    def wasm_project_media(self, project_id, attachment_id, **kw):
        """Images uploaded in the project's media tab (only if they belong to that project)."""
        project = request.env['wasm.project'].sudo().browse(project_id)
        if not project.exists() or not project.active or attachment_id not in project.attachment_ids.ids:
            raise request.not_found()
        attachment = request.env['ir.attachment'].sudo().browse(attachment_id)
        if not (attachment.mimetype or '').startswith('image/'):
            raise request.not_found()
        return self._wasm_stream(attachment, 'datas', filename=attachment.name)

    @http.route('/contactus', type='http', auth='public', website=True)
    def wasm_contactus(self, **kw):
        return request.render('wasm_website.contact_page_template', {
            'site_config': request.env['wasm.site.config'].sudo().get_config(),
        })

    @http.route('/contact-team', type='http', auth='public', website=True)
    def wasm_contact_team(self, **kw):
        return request.render('wasm_website.contact_team_page_template', {
            'site_config': request.env['wasm.site.config'].sudo().get_config(),
        })

    @http.route('/quote', type='http', auth='public', website=True)
    def wasm_quote(self, dept=None, service_id=None, **kw):
        services = request.env['wasm.service'].sudo().search(
            [('active', '=', True)], order='sequence, id'
        )
        selected_service_id = _parse_service_id(service_id)
        values = {
            'services': services,
            'selected_dept': dept if dept in ALLOWED_DEPARTMENTS else 'sales',
            'selected_service_id': selected_service_id,
        }
        return request.render('wasm_website.quote_page_template', values)

    @http.route('/quote/submit', type='http', auth='public', methods=['POST'],
                website=True, csrf=True)
    def wasm_quote_submit(self, **post):
        spam = _wasm_spam_reason(post)
        if spam:
            _logger.info('Quote form rejected (%s) from %s', spam, _client_ip())
            return request.redirect('/quote?error=%s' % ('rate_limit' if spam == 'rate_limit' else 'invalid'))

        # --- Input Validation ---
        customer_name = _clean(post, 'customer_name')
        phone = _clean(post, 'phone')
        email = _clean(post, 'email')
        project_location = _clean(post, 'project_location')

        if not customer_name or not phone or not email or not project_location:
            return request.redirect('/quote?error=missing_fields')
        if not _valid_contact(email, phone):
            return request.redirect('/quote?error=invalid_contact')

        customer_type = post.get('customer_type', 'company')
        if customer_type not in ALLOWED_CUSTOMER_TYPES:
            customer_type = 'company'

        project_type = post.get('project_type', 'commercial')
        if project_type not in ALLOWED_PROJECT_TYPES:
            project_type = 'commercial'

        department = post.get('department', 'sales')
        if department not in ALLOWED_DEPARTMENTS:
            department = 'sales'

        details = _clean(post, 'details')
        service_id = _parse_service_id(post.get('service_id'))
        area = _parse_amount(post.get('area'), 1e9)
        approx_budget = _parse_amount(post.get('approx_budget'), 1e12)
        expected_start_date = _parse_date(post.get('expected_start_date'))

        # --- Create Quote Request (e-mails are sent below, once the files are linked) ---
        Quote = request.env['wasm.quote.request'].sudo().with_context(wasm_defer_notifications=True)
        quote = Quote.create({
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
            'client_ip': _client_ip(),
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

            # Check the real content type, not only the extension
            sniffed = guess_mimetype(file_content[:4096]) or ''
            if sniffed in BLOCKED_MIMETYPES:
                _logger.warning('Quote %s: Rejected file %s (content type %s)', quote.name, uploaded_file.filename, sniffed)
                continue

            # Sanitize filename
            safe_filename = _clean_text(os.path.basename(uploaded_file.filename.replace('\\', '/')),
                                        single_line=True)[:120] or 'file%s' % ext.lower()

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
        quote._wasm_notify()

        return request.redirect(
            '/quote/thanks?token=%s' % quote.access_token
        )

    @http.route(['/contactus/submit', '/contact/submit'], type='http', auth='public', methods=['POST'],
                website=True, csrf=True)
    def wasm_contactus_submit(self, **post):
        spam = _wasm_spam_reason(post)
        if spam:
            _logger.info('Contact form rejected (%s) from %s', spam, _client_ip())
            return request.redirect('/contactus?error=%s' % ('rate_limit' if spam == 'rate_limit' else 'invalid'))

        customer_name = _clean(post, 'customer_name')
        phone = _clean(post, 'phone')
        email = _clean(post, 'email')
        project_location = _clean(post, 'project_location') or 'غير محدد'
        details = _clean(post, 'details')

        if not customer_name or not phone or not email or not details:
            return request.redirect('/contactus?error=missing_fields')
        if not _valid_contact(email, phone):
            return request.redirect('/contactus?error=invalid_contact')

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
            'source': 'contact',
            'client_ip': _client_ip(),
        })

        return request.redirect(f'/quote/thanks?token={quote.access_token}')

    @http.route('/quote/thanks', type='http', auth='public', website=True, sitemap=False)
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
        return request.render('wasm_website.location_page_template', {
            'site_config': request.env['wasm.site.config'].sudo().get_config()})

    @http.route(list(SEO_REDIRECTS), type='http', auth='public', website=True, sitemap=False)
    def wasm_seo_redirect(self, **kw):
        """Old / duplicate addresses -> one canonical URL (301 keeps search ranking)."""
        target = SEO_REDIRECTS.get(request.httprequest.path.rstrip('/') or '/', '/')
        return request.redirect(target, code=301)

    @http.route('/project/<int:project_id>', type='http', auth='public', website=True, sitemap=False)
    def wasm_project_legacy(self, project_id, **kw):
        return request.redirect('/projects/%s' % project_id, code=301)

    @http.route('/robots.txt', type='http', auth='public', sitemap=False)
    def wasm_robots_txt(self, **kw):
        config = request.env['wasm.site.config'].sudo()
        headers = [('Content-Type', 'text/plain; charset=utf-8'), ('Cache-Control', 'public, max-age=3600')]
        if config.wasm_hide_from_search():
            return request.make_response('User-agent: *\nDisallow: /\n', headers=headers)
        base = config.wasm_base_url(request.httprequest.url_root)
        lines = [
            '# ARFA Construction & Specialized Systems',
            'User-agent: *',
            'Allow: /',
            'Disallow: /web',
            'Disallow: /odoo',
            'Disallow: /my',
            'Disallow: /quote/thanks',
            'Disallow: /quote/submit',
            'Disallow: /contactus/submit',
            '',
            '# AI assistants and AI search engines are welcome to read the public pages',
        ]
        for bot in ('GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'Claude-User',
                    'PerplexityBot', 'Perplexity-User', 'Google-Extended', 'Applebot-Extended', 'Bingbot', 'CCBot'):
            lines += ['User-agent: %s' % bot, 'Allow: /', 'Disallow: /web', 'Disallow: /my', '']
        lines += ['Sitemap: %s/sitemap.xml' % base, '', '# Plain-language summary for AI tools: %s/llms.txt' % base]
        return request.make_response('\n'.join(lines) + '\n', headers=headers)

    @http.route(['/llms.txt', '/.well-known/llms.txt'], type='http', auth='public', sitemap=False)
    def wasm_llms_txt(self, **kw):
        """Markdown summary of the company for AI assistants / AI search (llms.txt convention)."""
        cfg = request.env['wasm.site.config'].sudo().get_config()
        text = cfg.wasm_llms_text(cfg.wasm_base_url(request.httprequest.url_root))
        return request.make_response(text, headers=[
            ('Content-Type', 'text/markdown; charset=utf-8'),
            ('Cache-Control', 'public, max-age=3600'),
        ])

    @http.route('/news', type='http', auth='public', website=True)
    def wasm_news(self, **kw):
        site_config = request.env['wasm.site.config'].sudo().get_config()
        articles = request.env['wasm.news'].sudo().search([('active', '=', True)], order='sequence, date desc, id desc')
        return request.render('wasm_website.news_page_template', {
            'site_config': site_config,
            'articles': articles,
        })

    @http.route('/news/<int:article_id>', type='http', auth='public', website=True, sitemap=_sitemap_news)
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


class WasmWebsite(Website):

    @http.route(sitemap=False)
    def website_info(self, **kwargs):
        """/website/info lists the installed apps and the Odoo version: not public on this site."""
        raise NotFound()
