# Run inside "odoo-bin shell": copy externally hosted images into the database so the new site does not
# depend on the old arfa-sa.com site (which this site will replace) or on third-party websites.
import base64
import requests

OLD_SITE_HOSTS = ('arfa-sa.com', 'www.arfa-sa.com')
OLD_SITE_LOCAL = 'http://127.0.0.1:8069'   # the current arfa-sa.com Odoo on this server


def fetch(url):
    try:
        from urllib.parse import urlsplit
        parts = urlsplit(url)
        if parts.hostname in OLD_SITE_HOSTS:   # ask the local old site directly (works before/after DNS changes)
            local = OLD_SITE_LOCAL + parts.path + ('?' + parts.query if parts.query else '')
            r = requests.get(local, headers={'Host': parts.hostname}, timeout=20)
        else:
            r = requests.get(url, timeout=20, headers={'User-Agent': 'Mozilla/5.0 (ARFA image import)'})
        ctype = r.headers.get('Content-Type', '')
        if r.status_code == 200 and ctype.startswith('image/') and len(r.content) > 200:
            return base64.b64encode(r.content)
        print('IMPORT skip %s (HTTP %s, %s)' % (url, r.status_code, ctype))
    except Exception as e:
        print('IMPORT skip %s (%s)' % (url, e))
    return False


done = 0
for item in env['wasm.content.item'].with_context(active_test=False).search([('image', '=', False), ('image_url', '!=', False)]):
    if item.image_url.startswith('http'):
        data = fetch(item.image_url)
        if data:
            item.image = data
            done += 1
for partner in env['wasm.partner'].with_context(active_test=False).search([('logo', '=', False), ('logo_url', '!=', False)]):
    if partner.logo_url.startswith('http'):
        data = fetch(partner.logo_url)
        if data:
            partner.logo = data
            done += 1
env.cr.commit()
print('IMPORT done: %s image(s) copied into the database' % done)
