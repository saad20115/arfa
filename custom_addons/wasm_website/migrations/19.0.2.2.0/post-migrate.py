# -*- coding: utf-8 -*-
"""19.0.2.2.0: production hardening (security audit + SEO + performance).

* security: the public user and the portal template user had been added to both wasm
  groups and "مدير عام عرفة الهندسية" implied Settings/Administration, so anonymous
  visitors were administrators (e.g. /web/content/<id> of uploaded quote files).
  The wasm groups get exactly the implied groups of the XML, external users leave the
  wasm groups, the public/portal template users keep only their own group, sign-up is
  by invitation only (auth_signup.invitation_scope = b2b);
* SEO: cached sitemaps are deleted, website.page records duplicating controller routes
  are no longer indexed, the old /about-us menu URL becomes /about;
* performance: oversized images already stored are re-encoded (cards 1200 px, banners
  1920 px, JPEG q80).
Everything lives in content_setup.py (also used by the install hook) and is idempotent.
"""
import logging

from odoo import SUPERUSER_ID, api

from odoo.addons.wasm_website.content_setup import (
    wasm_optimize_existing_images, wasm_security_hardening, wasm_seo_housekeeping,
)

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    security = wasm_security_hardening(env)
    seo = wasm_seo_housekeeping(env)
    env['wasm.text']._wasm_sync_defaults()      # new text keys of this version
    images = wasm_optimize_existing_images(env)
    _logger.warning('wasm_website 19.0.2.2.0: %s security change(s), %s SEO change(s), %s image(s) optimised',
                    len(security), len(seo), images)
