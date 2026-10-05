# -*- coding: utf-8 -*-
"""Create the editable website content (texts, cards, services, galleries, news).

Called on install (post_init_hook) and by the 19.0.2.0.0 migration. Everything is
idempotent: a section / record that already has content is left untouched, so the
admin's edits are never overwritten.
"""
import logging

from odoo.fields import Command
from odoo.tools import SQL

from .models.texts import legacy_services
from .models.wasm_site_config import DEFAULT_IMAGES

_logger = logging.getLogger(__name__)

# Projects shipped with the module: default photo when none was uploaded.
PROJECT_IMAGES = {
    'project_ritz_carlton': 'static/src/img/project_conference_ritz.jpg',
    'project_qirwan_kitchen': 'static/src/img/project_qirwan_kitchen.jpg',
    'project_sudair_factories': 'static/src/img/project_sudair_industrial.jpg',
    'project_intercontinental_taif': 'static/src/img/project_intercontinental_taif.jpg',
    'project_mina_hospital': 'static/src/img/project_mina_hospital.jpg',
    'project_janadriyah_towers': 'static/src/img/project_janadriyah_towers.jpg',
    'project_sofitel_makkah': 'static/src/img/project_sofitel_makkah.jpg',
    'project_ramada_meridien': 'static/src/img/project_ramada_meridien.jpg',
}

# Photos that the projects page used to show when the gallery was empty.
DEFAULT_GALLERY = [
    'industrial_park_sudair.webp', 'nora_univ_1.webp', 'nora_univ_2.webp', 'gallery_img_1.webp', 'gallery_img_2.webp',
    'gallery_img_5.webp', 'gallery_img_6.webp', 'gallery_img_8.webp', 'gallery_img_9.webp', 'gallery_img_10.webp',
    'gallery_img_11.webp', 'gallery_img_14.webp', 'gallery_img_17.webp',
]


def _file(env, path):
    return env['wasm.content.item']._wasm_read_module_file(path)


def _table_has_column(cr, table, column):
    cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s", (table, column))
    return bool(cr.fetchone())


def _legacy_config_values(env):
    """Values of the old fixed homepage fields of wasm.site.config (columns are kept by Odoo)."""
    cr = env.cr
    if not _table_has_column(cr, 'wasm_site_config', 'pillar1_title_en'):
        return None
    cr.execute('SELECT * FROM wasm_site_config ORDER BY id LIMIT 1')
    row = cr.dictfetchone()
    return row


def _legacy_config_image(env, config_id, field):
    att = env['ir.attachment'].sudo().search([
        ('res_model', '=', 'wasm.site.config'), ('res_id', '=', config_id), ('res_field', '=', field)], limit=1)
    return att.datas if att else False


def _items_from_legacy_config(env, row):
    Item = env['wasm.content.item'].sudo().with_context(active_test=False)
    if not Item.search_count([('section', '=', 'pillar')]):
        vals = []
        for i in range(1, 4):
            vals.append({
                'section': 'pillar', 'sequence': i * 10,
                'title_en': row.get('pillar%d_title_en' % i), 'title_ar': row.get('pillar%d_title_ar' % i),
                'desc_en': row.get('pillar%d_desc_en' % i), 'desc_ar': row.get('pillar%d_desc_ar' % i),
                'link_url': row.get('pillar%d_link' % i) or '/services',
                'link_label_en': 'Explore Services', 'link_label_ar': 'استكشف الخدمات',
                'image': _legacy_config_image(env, row['id'], 'pillar%d_img' % i)
                or _file(env, DEFAULT_IMAGES['pillar%d_img' % i]),
            })
        Item.create(vals)
    if not Item.search_count([('section', '=', 'stat')]):
        Item.create([{
            'section': 'stat', 'sequence': i * 10, 'value': row.get('stat%d_val' % i),
            'title_en': row.get('stat%d_label_en' % i), 'title_ar': row.get('stat%d_label_ar' % i),
        } for i in range(1, 5)])
    if not Item.search_count([('section', '=', 'why')]):
        Item.create([{
            'section': 'why', 'sequence': i * 10,
            'title_en': row.get('why%d_title_en' % i), 'title_ar': row.get('why%d_title_ar' % i),
            'desc_en': row.get('why%d_desc_en' % i), 'desc_ar': row.get('why%d_desc_ar' % i),
            'image': _legacy_config_image(env, row['id'], 'why%d_img' % i) or _file(env, DEFAULT_IMAGES['why%d_img' % i]),
        } for i in range(1, 7)])


def _set_translation(env, record, field, ar_value):
    """Store the Arabic translation of a translatable field (works even if Arabic is not active)."""
    if not ar_value:
        return
    env.cr.execute(SQL(
        "UPDATE %s SET %s = COALESCE(%s, '{}'::jsonb) || jsonb_build_object('ar_001', %s::text) WHERE id = %s",
        SQL.identifier(record._table), SQL.identifier(field), SQL.identifier(field), ar_value, record.id))
    record.invalidate_recordset([field])


def _setup_services(env, row):
    """One wasm.service per service page, filled from the old hardcoded pages and homepage cards."""
    Service = env['wasm.service'].sudo().with_context(active_test=False, lang='en_US')
    Media = env['wasm.gallery.image'].sudo()
    # card order / texts / images of the old homepage slider, keyed by slug
    cards = {}
    if row:
        for n in range(1, 9):
            url = (row.get('srv%d_url' % n) or '').strip('/')
            if url:
                cards[url] = {'n': n, 'title': row.get('srv%d_title_en' % n), 'desc': row.get('srv%d_desc_en' % n),
                              'desc_ar': row.get('srv%d_desc_ar' % n),
                              'img': _legacy_config_image(env, row['id'], 'srv%d_img' % n)}
    # services created by the module's old demo data (duplicates of the real ones)
    demo = env['ir.model.data'].sudo().search([('module', '=', 'wasm_website'), ('model', '=', 'wasm.service'),
                                                ('name', 'in', ['service_civil', 'service_mep', 'service_hvac', 'service_finishing'])])
    demo_ids = set(demo.mapped('res_id'))
    for order, info in enumerate(legacy_services.SERVICES, start=1):
        slug = info['slug']
        card = cards.get(slug, {})
        service = Service.search([('slug', '=', slug), ('id', 'not in', list(demo_ids))], limit=1)
        if not service and card.get('title'):
            service = Service.search([('name', '=', card['title']), ('id', 'not in', list(demo_ids))], limit=1)
        if service and service.page_title:
            continue  # already set up
        vals = {
            'slug': slug,
            'page_title': info['title_en'],
            'badge': info['badge_en'],
            'intro': info['subtitle_en'],
            'features': '\n'.join(info['features_en']),
            'icon': info['icon'],
            'show_on_home': True,
            'active': True,
            'sequence': (card.get('n') or order) * 10,
            'banner_image': _file(env, info['bg_img']),
            'card_description': card.get('desc') or False,
        }
        if not service:
            vals.update({'name': card.get('title') or info['title_en'], 'short_description': card.get('desc') or '',
                         'category': 'general'})
            service = Service.create(vals)
        else:
            service.write(vals)
            if not service.short_description and card.get('desc'):
                service.short_description = card['desc']
        if not service.image:
            image = card.get('img') or _file(env, DEFAULT_IMAGES.get('srv%d_img' % card['n']) if card.get('n') else info['gallery_imgs'][0])
            if image:
                service.image = image
        for field, key in (('page_title', 'title_ar'), ('badge', 'badge_ar'), ('intro', 'subtitle_ar')):
            _set_translation(env, service, field, info.get(key))
        _set_translation(env, service, 'features', '\n'.join(info.get('features_ar') or []))
        _set_translation(env, service, 'card_description', card.get('desc_ar'))
        if not service.media_ids:
            Media.create([{
                'name': False,
                'media_type': 'image',
                'image': _file(env, path),
                'service_id': service.id,
                'show_in_gallery': False,
                'sequence': i * 10,
            } for i, path in enumerate(info['gallery_imgs'], start=1) if _file(env, path)])
    if demo_ids:
        Service.browse(list(demo_ids)).exists().write({'active': False, 'show_on_home': False})


def _setup_project_images(env):
    for xmlid, path in PROJECT_IMAGES.items():
        project = env.ref('wasm_website.%s' % xmlid, raise_if_not_found=False)
        if project and not project.sudo().image:
            data = _file(env, path)
            if data:
                project.sudo().image = data


def _setup_gallery(env):
    Media = env['wasm.gallery.image'].sudo().with_context(active_test=False)
    if Media.search_count([('service_id', '=', False)]):
        return
    vals = []
    for i, name in enumerate(DEFAULT_GALLERY, start=1):
        data = _file(env, 'static/src/img/official_live_projects/' + name)
        if data:
            vals.append({'name': False, 'media_type': 'image', 'image': data,
                         'show_in_gallery': True, 'sequence': i * 10})
    Media.create(vals)


def _setup_news(env):
    from .models.texts import t_quote_news
    seeds = getattr(t_quote_news, 'NEWS', [])
    News = env['wasm.news'].sudo().with_context(active_test=False)
    if not seeds or News.search_count([]):
        return
    for seq, seed in enumerate(seeds, start=1):
        vals = {k: v for k, v in seed.items() if k in News._fields and k != 'image'}
        vals.setdefault('sequence', seq * 10)
        if seed.get('image_file'):
            vals['image'] = _file(env, seed['image_file'])
        News.create(vals)


# ---------------------------------------------------------------------------
# 19.0.2.2.0: security hardening, SEO housekeeping, image optimisation
# (called by the install hook and by the 19.0.2.2.0 migration; all idempotent)
# ---------------------------------------------------------------------------
WASM_GROUP_IMPLIED = {
    # group xmlid -> the only groups it may imply (as declared in security/wasm_security.xml)
    'wasm_website.group_wasm_user': ('base.group_user',),
    'wasm_website.group_wasm_manager': ('wasm_website.group_wasm_user',),
}

def _controller_urls():
    """Static URLs answered by this module's controllers: a website.page with the same URL is a
    duplicate sitemap entry (the controller answers; the page record only helps the page manager)."""
    from .controllers.main import SEO_REDIRECTS
    from .models.wasm_service import LEGACY_SLUGS
    urls = {'/', '/about', '/our-company', '/services', '/projects', '/contactus', '/contact-team', '/quote',
            '/location', '/news', '/company-profile'}
    urls.update(SEO_REDIRECTS)
    urls.update('/%s' % slug for slug in LEGACY_SLUGS)
    return urls


def wasm_security_hardening(env):
    """Remove the dangerous grants found in production databases.

    * the wasm groups imply exactly what the XML declares (a manual change had made
      "مدير عام" imply Settings/Administration);
    * the public user and the portal template user keep only their user-type group (they
      had been added to both wasm groups: anonymous visitors became administrators);
    * no portal/public (share) user stays in a wasm group;
    * sign-up is by invitation only.
    Returns a list of human readable changes (also logged).
    """
    changes = []
    Users = env['res.users'].sudo().with_context(active_test=False)
    ref = lambda xmlid: env.ref(xmlid, raise_if_not_found=False)  # noqa: E731
    g_system, g_user = ref('base.group_system'), ref('base.group_user')
    g_public, g_portal = ref('base.group_public'), ref('base.group_portal')
    wasm_groups = env['res.groups'].sudo().browse()
    admins_before = Users.search([('all_group_ids', 'in', g_system.ids)]) if g_system else Users

    # 1. implied groups exactly as declared
    for xmlid, implied_xmlids in WASM_GROUP_IMPLIED.items():
        group = ref(xmlid)
        if not group:
            continue
        group = group.sudo()
        wasm_groups |= group
        allowed = env['res.groups'].sudo().browse([g.id for g in map(ref, implied_xmlids) if g])
        extra = group.implied_ids - allowed
        missing = allowed - group.implied_ids
        if extra or missing:
            group.write({'implied_ids': [Command.unlink(g.id) for g in extra] + [Command.link(g.id) for g in missing]})
            changes.append('%s: implied groups removed %s, added %s' % (
                xmlid, extra.mapped('full_name'), missing.mapped('full_name')))

    # 2. public user / portal template: only their own user-type group
    for user_xmlid, keep in (('base.public_user', g_public), ('base.template_portal_user_id', g_portal)):
        user = ref(user_xmlid)
        if not user or not keep:
            continue
        user = user.sudo().with_context(active_test=False)
        extra = user.group_ids - keep
        if extra or keep not in user.group_ids:
            user.write({'group_ids': [Command.set(keep.ids)]})
            changes.append('%s (%s): groups removed %s' % (user_xmlid, user.login, extra.mapped('full_name')))

    # 3. groups implied by public/portal must never lead to internal access
    for group in (g_public | g_portal) if (g_public and g_portal) else env['res.groups']:
        bad = group.implied_ids.filtered(lambda g: g_user in (g | g.all_implied_ids))
        if bad:
            group.write({'implied_ids': [Command.unlink(g.id) for g in bad]})
            changes.append('%s: implied internal groups removed %s' % (group.full_name, bad.mapped('full_name')))

    # 4. other external users must not sit in a wasm group
    if wasm_groups:
        external_ids = [g.id for g in (g_public, g_portal) if g]
        externals = Users.search([('group_ids', 'in', wasm_groups.ids), '|', ('share', '=', True),
                                  ('group_ids', 'in', external_ids)])
        for user in externals:
            user.write({'group_ids': [Command.unlink(g.id) for g in wasm_groups]})
            changes.append('user %s (%s): removed from %s' % (user.id, user.login, wasm_groups.mapped('full_name')))

    # 5. stored "share" flag follows the groups again
    touched = Users.browse([u.id for u in (ref('base.public_user'), ref('base.template_portal_user_id')) if u])
    touched |= Users.search([('group_ids', 'in', [g.id for g in (g_public, g_portal) if g])])
    if touched:
        touched.invalidate_recordset(['all_group_ids'])
        touched._compute_share()
        touched.flush_recordset(['share'])

    if g_system:
        lost = admins_before - Users.search([('all_group_ids', 'in', g_system.ids)])
        if lost:
            changes.append('users no longer administrators (was only through a wasm group): %s'
                           % lost.mapped('login'))

    # 6. no free sign-up of portal accounts
    ICP = env['ir.config_parameter'].sudo()
    if ICP.get_param('auth_signup.invitation_scope', 'b2b') != 'b2b':
        ICP.set_param('auth_signup.invitation_scope', 'b2b')
        changes.append('auth_signup.invitation_scope set to b2b (sign-up by invitation only)')

    for line in changes:
        _logger.warning('wasm_website security hardening: %s', line)
    return changes


def wasm_seo_housekeeping(env):
    """Clean sitemap sources: cached sitemaps, duplicate page records, old menu URLs."""
    changes = []
    sitemaps = env['ir.attachment'].sudo().search([('url', '=like', '/sitemap%.xml')])
    if sitemaps:
        changes.append('cached sitemaps deleted: %s' % sitemaps.mapped('url'))
        sitemaps.unlink()
    urls = _controller_urls()
    Page = env['website.page'].sudo().with_context(active_test=False)
    duplicates = Page.search([('url', 'in', list(urls)), ('url', '!=', '/'), ('website_indexed', '=', True)])
    if duplicates:
        changes.append('website.page not indexed (URL served by a controller): %s' % duplicates.mapped('url'))
        duplicates.write({'website_indexed': False})
    menus = env['website.menu'].sudo().search([('url', '=', '/about-us')])
    if menus:
        menus.write({'url': '/about'})
        changes.append('website.menu %s: /about-us -> /about' % menus.ids)
    for line in changes:
        _logger.info('wasm_website SEO housekeeping: %s', line)
    return changes


def wasm_optimize_existing_images(env):
    """Re-encode oversized images already stored in the website records."""
    total = 0
    for model_name in sorted(env.registry.models):
        Model = env[model_name]
        if Model._abstract or Model._transient or not getattr(Model, '_wasm_image_fields', None):
            continue
        records = Model.sudo().with_context(active_test=False).search([])
        count = records._wasm_optimize_existing_images()
        if count:
            _logger.info('wasm_website: %s image(s) optimised on %s', count, model_name)
        total += count
    return total


def wasm_install_content(env):
    env['wasm.text']._wasm_sync_defaults()
    row = _legacy_config_values(env)
    if row:
        _items_from_legacy_config(env, row)
    env['wasm.content.item']._wasm_seed()
    _setup_services(env, row)
    _setup_project_images(env)
    _setup_gallery(env)
    _setup_news(env)
    _logger.info('wasm_website: editable website content ready')
