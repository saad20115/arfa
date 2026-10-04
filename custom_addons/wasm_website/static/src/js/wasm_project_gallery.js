/** @odoo-module **/
/*
 * Project page gallery: category filter tabs + a lightweight lightbox.
 * - Filtering only toggles a class kept in memory; it is reset when the
 *   Website Builder enters edit mode, so nothing runtime-only gets saved.
 * - The lightbox lives outside #wrap (appended to <body>), never in the page.
 */
(function () {
    'use strict';

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
            '<button type="button" class="arfa-lb-close" aria-label="Close">&times;</button>' +
            '<button type="button" class="arfa-lb-nav arfa-lb-prev" aria-label="Previous">&#8249;</button>' +
            '<figure class="arfa-lb-figure"><img alt=""/><figcaption></figcaption></figure>' +
            '<button type="button" class="arfa-lb-nav arfa-lb-next" aria-label="Next">&#8250;</button>';
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

    function show(i) {
        if (!list.length) return;
        index = (i + list.length) % list.length;
        var tile = list[index];
        var img = box.querySelector('img');
        img.src = tile.getAttribute('href');
        img.alt = tile.querySelector('img') ? tile.querySelector('img').alt : '';
        box.querySelector('figcaption').textContent = tile.getAttribute('data-caption') || '';
    }

    function open(root, tile) {
        buildBox();
        list = Array.prototype.filter.call(root.querySelectorAll('.arfa-pd-tile'), function (t) {
            return !t.classList.contains('is-hidden');
        });
        show(list.indexOf(tile));
        box.classList.add('is-open');
        document.documentElement.classList.add('arfa-lb-lock');
        box.querySelector('.arfa-lb-close').focus();
    }

    function close() {
        if (!box) return;
        box.classList.remove('is-open');
        document.documentElement.classList.remove('arfa-lb-lock');
    }

    function boot() {
        var roots = document.querySelectorAll('.arfa-pd-gallery');
        if (!roots.length) return;
        roots.forEach(function (root) {
            root.addEventListener('click', function (ev) {
                if (isEditMode()) return;
                var btn = ev.target.closest('.arfa-pd-filter');
                if (btn) { applyFilter(root, btn.getAttribute('data-filter')); return; }
                var tile = ev.target.closest('.arfa-pd-tile');
                if (tile) { ev.preventDefault(); open(root, tile); }
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
