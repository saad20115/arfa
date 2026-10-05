# -*- coding: utf-8 -*-
"""Shared helpers of the website models.

* ``wasm.image.mixin``: uploaded photos are re-encoded to a sane size before they are
  stored (phones and stock sites deliver 3-10 MB images that the site shows at 400 px).
* ``wasm_check_urls``: URL fields may only hold http(s) links or site-relative paths
  (no ``javascript:``, ``data:`` or protocol-relative ``//host`` values).
"""
import base64
import logging
import re

from odoo import _, api, models
from odoo.exceptions import ValidationError
from odoo.tools.image import IMAGE_MAX_RESOLUTION, binary_to_image, image_apply_opt, image_fix_orientation
from odoo.tools.mimetypes import guess_mimetype

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Images
# ---------------------------------------------------------------------------
IMAGE_MAX_BYTES = 350 * 1024        # larger files are always re-encoded
IMAGE_JPEG_QUALITY = 80
CARD_PX = 1200                      # cards, news covers, service cards
ITEM_PX = 800                       # small content cards (pillars, why-us, team: shown at ~400 px)
BANNER_PX = 1920                    # hero / banners / gallery photos
# Odoo only enables the JPEG/PNG/BMP/GIF/ICO decoders of Pillow (odoo.tools.image): WebP files are
# kept as uploaded (they are already compressed), like Odoo's own image fields do.
_RASTER_MIMETYPES = ('image/jpeg', 'image/png', 'image/bmp')


def _has_transparency(image):
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        alpha = image.convert('RGBA').getchannel('A')
        return alpha.getextrema()[0] < 255
    return False


def wasm_optimize_image_bytes(raw, max_px, max_bytes=IMAGE_MAX_BYTES, quality=IMAGE_JPEG_QUALITY):
    """Return a lighter encoding of ``raw`` (bytes) or ``raw`` itself when nothing is gained.

    Re-encodes when the file is bigger than ``max_bytes`` or its longest side exceeds
    ``max_px``: resized to ``max_px`` (ratio kept) and saved as JPEG ``quality``;
    images that really use transparency stay PNG. SVG, GIF (animations), WebP and anything
    that is not a JPEG/PNG/BMP image are returned untouched.
    """
    if not raw:
        return raw
    mimetype = guess_mimetype(raw[:1024], default='')
    if mimetype not in _RASTER_MIMETYPES:
        return raw
    try:
        image = binary_to_image(raw)
        width, height = image.size
        if width * height > IMAGE_MAX_RESOLUTION:
            return raw          # Odoo's own field validation reports it
        if len(raw) <= max_bytes and max(width, height) <= max_px:
            return raw
        image = image_fix_orientation(image)
        if max(image.size) > max_px:
            image.thumbnail((max_px, max_px), resample=3)   # 3 = LANCZOS
        if _has_transparency(image):
            output = image_apply_opt(image.convert('RGBA'), 'PNG', optimize=True)
        else:
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            output = image_apply_opt(image, 'JPEG', quality=quality, optimize=True, progressive=True)
    except Exception:  # never block a save because of an exotic file
        _logger.warning('wasm_website: image optimisation skipped', exc_info=True)
        return raw
    if len(output) >= len(raw) and max(width, height) <= max_px:
        return raw
    return output


class WasmImageMixin(models.AbstractModel):
    _name = 'wasm.image.mixin'
    _description = 'Website image optimisation (ARFA)'

    # field name -> longest side in px; set on every model that inherits the mixin
    _wasm_image_fields = {}

    @api.model
    def _wasm_optimize_b64(self, value, max_px):
        if not value or not isinstance(value, (str, bytes)):
            return value
        try:
            raw = base64.b64decode(value, validate=False)
        except Exception:
            return value
        optimized = wasm_optimize_image_bytes(raw, max_px)
        if optimized is raw:
            return value
        return base64.b64encode(optimized)

    @api.model
    def _wasm_optimize_vals(self, vals):
        if self.env.context.get('wasm_skip_image_optimize'):
            return vals
        todo = {f: px for f, px in self._wasm_image_fields.items() if vals.get(f)}
        if not todo:
            return vals
        vals = dict(vals)
        for field_name, max_px in todo.items():
            vals[field_name] = self._wasm_optimize_b64(vals[field_name], max_px)
        return vals

    @api.model_create_multi
    def create(self, vals_list):
        return super().create([self._wasm_optimize_vals(vals) for vals in vals_list])

    def write(self, vals):
        return super().write(self._wasm_optimize_vals(vals))

    def _wasm_optimize_existing_images(self):
        """Re-encode images already stored (migration). Returns the number of images changed."""
        changed = 0
        records = self.with_context(active_test=False, bin_size=False, wasm_skip_image_optimize=True)
        for record in records:
            vals = {}
            for field_name, max_px in self._wasm_image_fields.items():
                value = record[field_name]
                if not value:
                    continue
                new_value = record._wasm_optimize_b64(value, max_px)
                if new_value is not value and new_value != value:
                    vals[field_name] = new_value
            if vals:
                record.write(vals)
                changed += len(vals)
        return changed


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
_HTTP_RE = re.compile(r'^https?://[^\s/?#\\]+[^\s\\]*$', re.IGNORECASE)
_RELATIVE_RE = re.compile(r'^/(?![/\\])[^\s\\]*$')
_LINK_EXTRA_RE = re.compile(r'^(?:mailto:[^\s<>"\\]+|tel:[0-9+()\-. ]+|#[\w\-]*|\{(?:phone|mobile|whatsapp|email)\})$',
                            re.IGNORECASE)
MAP_EMBED_PREFIX = 'https://www.google.com/maps/embed'


def wasm_url_is_safe(value, extra_link=False):
    """True for empty values, http(s) links and site-relative paths (``/x``, not ``//x``).

    ``extra_link`` also accepts mailto:/tel: links, ``#anchors`` and the contact placeholders
    ({phone} {mobile} {whatsapp} {email}) used by menu/footer link fields.
    """
    if not value:
        return True
    value = value.strip()
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return False
    if _HTTP_RE.match(value) or _RELATIVE_RE.match(value):
        return True
    return bool(extra_link and _LINK_EXTRA_RE.match(value))


def wasm_check_urls(records, url_fields=(), link_fields=(), embed_fields=()):
    """Raise ValidationError when one of the fields holds a value that is not a safe URL."""
    for rec in records:
        for names, check in ((url_fields, lambda v: wasm_url_is_safe(v)),
                             (link_fields, lambda v: wasm_url_is_safe(v, extra_link=True)),
                             (embed_fields, lambda v: not v or (v.strip().startswith(MAP_EMBED_PREFIX)
                                                                and wasm_url_is_safe(v)))):
            for name in names:
                value = rec[name]
                if value and not check(value):
                    label = rec._fields[name].string or name
                    if name in embed_fields:
                        raise ValidationError(_(
                            '"%(field)s": use the Google Maps embed link (it must start with %(prefix)s).\n'
                            'استخدم رابط التضمين من خرائط جوجل (يبدأ بـ %(prefix)s).',
                            field=label, prefix=MAP_EMBED_PREFIX))
                    raise ValidationError(_(
                        '"%(field)s": only links starting with https:// (or http://) or a page path '
                        'starting with / are allowed.\n'
                        'يُسمح فقط بروابط تبدأ بـ https:// أو بمسار صفحة يبدأ بـ /.',
                        field=label))
