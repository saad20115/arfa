/** @odoo-module **/
/*
 * Project page gallery: category filter tabs + a lightweight lightbox (photos and videos).
 * - Filtering only toggles a class kept in memory; it is reset when the
 *   Website Builder enters edit mode, so nothing runtime-only gets saved.
 * - The lightbox lives outside #wrap (appended to <body>), never in the page.
 * - Roots: `.arfa-pd-gallery` (project page) and `.arfa-lb-root` (projects page strip).
 *   Tiles: `.arfa-pd-tile` / `.arfa-lb-item`. A video tile has data-type="video" and
 *   data-video-src (mp4, played in <video>) or data-embed (YouTube/Vimeo, played in an iframe).
 * - Button labels (aria) come from the root's data-lb-close / data-lb-prev / data-lb-next
 *   attributes (editable website texts rendered by the template).
 */
(function () {
    'use strict';

    var ROOT_SELECTOR = '.arfa-pd-gallery, .arfa-lb-root';
    var TILE_SELECTOR = '.arfa-pd-tile, .arfa-lb-item';

    function isEditMode() {
        var b = document.body;
        return !!(b && (b.classList.contains('editor_enable') || b.classList.contains('o_edit_mode') ||
            /[?&]enable_editor=1/.test(window.location.search)));
    }

    function applyFilter(root, key) {
        root.querySelectorAll('.arfa-pd-filter').forEach(function (btn) {
            var on = btn.getAttribute('data-filter') === key;
            btn.classList.toggle('is-active', on);
            btn.setAttribute('aria-selected', on ? 'true' : 'false');
        });
        root.querySelectorAll('.arfa-pd-tile').forEach(function (tile) {
            var show = key === '*' || tile.getAttribute('data-cat') === key;
            tile.classList.toggle('is-hidden', !show);
        });
    }

    /* ---------- Lightbox ---------- */
    var box = null, list = [], index = 0;

    function buildBox() {
        if (box) return box;
        box = document.createElement('div');
        box.className = 'arfa-lightbox';
        box.setAttribute('role', 'dialog');
        box.setAttribute('aria-modal', 'true');
        box.innerHTML =
            '<button type="button" class="arfa-lb-close">&times;</button>' +
            '<button type="button" class="arfa-lb-nav arfa-lb-prev">&#8249;</button>' +
            '<figure class="arfa-lb-figure"><img alt=""/><div class="arfa-lb-media"></div><figcaption></figcaption></figure>' +
            '<button type="button" class="arfa-lb-nav arfa-lb-next">&#8250;</button>';
        document.body.appendChild(box);
        box.addEventListener('click', function (ev) {
            if (ev.target === box || ev.target.classList.contains('arfa-lb-close')) { close(); }
            else if (ev.target.classList.contains('arfa-lb-prev')) { show(index - 1); }
            else if (ev.target.classList.contains('arfa-lb-next')) { show(index + 1); }
        });
        document.addEventListener('keydown', function (ev) {
            if (!box.classList.contains('is-open')) return;
            if (ev.key === 'Escape') close();
            if (ev.key === 'ArrowLeft') show(index - 1);
            if (ev.key === 'ArrowRight') show(index + 1);
        });
        return box;
    }

    function setLabels(root) {
        [['.arfa-lb-close', 'data-lb-close'], ['.arfa-lb-prev', 'data-lb-prev'], ['.arfa-lb-next', 'data-lb-next']]
            .forEach(function (pair) {
                var btn = box.querySelector(pair[0]);
                var label = root.getAttribute(pair[1]);
                if (label) { btn.setAttribute('aria-label', label); btn.setAttribute('title', label); }
                else { btn.removeAttribute('aria-label'); btn.removeAttribute('title'); }
            });
    }

    /* Removing the <video>/<iframe> stops playback (used on next/prev/close). */
    function clearMedia() {
        if (!box) return;
        var media = box.querySelector('.arfa-lb-media');
        var video = media.querySelector('video');
        if (video) { try { video.pause(); } catch (e) { /* ignore */ } }
        media.innerHTML = '';
    }

    function withAutoplay(url) {
        return url + (url.indexOf('?') === -1 ? '?' : '&') + 'autoplay=1';
    }

    function show(i) {
        if (!list.length) return;
        index = (i + list.length) % list.length;
        var tile = list[index];
        var fig = box.querySelector('.arfa-lb-figure');
        var img = box.querySelector('img');
        var media = box.querySelector('.arfa-lb-media');
        var thumb = tile.querySelector('img');
        clearMedia();
        if (tile.getAttribute('data-type') === 'video') {
            fig.classList.add('is-video');
            img.removeAttribute('src');
            img.alt = '';
            var embed = tile.getAttribute('data-embed');
            var src = tile.getAttribute('data-video-src');
            if (embed) {
                var frame = document.createElement('iframe');
                frame.src = withAutoplay(embed);
                frame.setAttribute('allowfullscreen', 'allowfullscreen');
                frame.setAttribute('allow', 'autoplay; encrypted-media; picture-in-picture; fullscreen');
                frame.title = tile.getAttribute('data-caption') || '';
                media.appendChild(frame);
            } else if (src) {
                var video = document.createElement('video');
                video.controls = true;
                video.autoplay = true;
                video.setAttribute('playsinline', 'playsinline');
                video.preload = 'metadata';
                var poster = tile.getAttribute('data-poster');
                if (poster) video.poster = poster;
                var source = document.createElement('source');
                source.src = src;
                source.type = 'video/mp4';
                video.appendChild(source);
                media.appendChild(video);
            }
        } else {
            fig.classList.remove('is-video');
            img.src = tile.getAttribute('href');
            img.alt = thumb ? thumb.alt : '';
        }
        box.querySelector('figcaption').textContent = tile.getAttribute('data-caption') || '';
    }

    function open(root, tile) {
        buildBox();
        setLabels(root);
        list = Array.prototype.filter.call(root.querySelectorAll(TILE_SELECTOR), function (t) {
            return !t.classList.contains('is-hidden') && !t.classList.contains('wasm-slider-clone');
        });
        var i = list.indexOf(tile);
        if (i === -1) {
            /* clicked a marquee clone: open its original */
            var key = tile.getAttribute('data-lb-key');
            list.some(function (t, n) {
                if (key && t.getAttribute('data-lb-key') === key) { i = n; return true; }
                return false;
            });
        }
        show(Math.max(i, 0));
        box.classList.toggle('is-single', list.length < 2);
        box.classList.add('is-open');
        document.documentElement.classList.add('arfa-lb-lock');
        box.querySelector('.arfa-lb-close').focus();
    }

    function close() {
        if (!box) return;
        clearMedia();
        box.classList.remove('is-open');
        document.documentElement.classList.remove('arfa-lb-lock');
    }

    function boot() {
        var roots = document.querySelectorAll(ROOT_SELECTOR);
        if (!roots.length) return;
        roots.forEach(function (root) {
            root.addEventListener('click', function (ev) {
                if (isEditMode()) return;
                var btn = ev.target.closest('.arfa-pd-filter');
                if (btn) { applyFilter(root, btn.getAttribute('data-filter')); return; }
                var tile = ev.target.closest(TILE_SELECTOR);
                if (tile && root.contains(tile)) { ev.preventDefault(); open(root, tile); }
            });
        });
        if (window.MutationObserver && document.body) {
            new MutationObserver(function () {
                if (isEditMode()) { roots.forEach(function (root) { applyFilter(root, '*'); }); close(); }
            }).observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
