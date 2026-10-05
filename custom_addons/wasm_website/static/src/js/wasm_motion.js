/** @odoo-module **/
/*
 * Scroll animations for the whole site (ARFA).
 *  - Reveal: section titles, cards, stats, project-page blocks and gallery tiles
 *    fade / slide in when they enter the screen, with a small stagger.
 *  - Count-up: numbers like "150+", "1,200,000+", "85+" count up once.
 *
 * Safety:
 *  - Hiding is only active while <html> has the class "arfa-anim" (set here),
 *    so if this script does not run, everything stays visible.
 *  - Nothing runs in Website Builder edit mode; on entering edit mode every
 *    element is shown and every number restored, so the editor saves clean HTML.
 *  - Respects "reduce motion" accessibility settings.
 */
(function () {
    'use strict';

    var REVEAL = [
        '.wasm-section-title',
        '.wasm-hover-card',
        '.wasm-pillar-card',
        '.wasm-stat-box',
        '.wasm-video-card',
        '.arfa-pd-cover',
        '.arfa-pd-facts',
        '.arfa-pd-acc',
        '.arfa-pd-gallery-head',
        '.arfa-pd-tile',
        '.arfa-pd-pager-inner > *',
        '.wasm-footer .col-lg-4, .wasm-footer .col-lg-2, .wasm-footer .col-lg-3'
    ].join(',');
    var COUNT = '.wasm-stat-number, .arfa-count';

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var root = document.documentElement;
    var io = null;
    var counted = new WeakMap();

    function isEditMode() {
        var b = document.body;
        return !!(b && (b.classList.contains('editor_enable') || b.classList.contains('o_edit_mode') ||
            /[?&]enable_editor=1/.test(window.location.search)));
    }

    /* ---------- count-up ---------- */
    function parseNumber(text) {
        var m = (text || '').match(/^(\D*)([\d][\d,\.]*)(.*)$/);
        if (!m) return null;
        var raw = m[2];
        var value = parseFloat(raw.replace(/,/g, ''));
        if (!isFinite(value) || value === 0) return null;
        return { prefix: m[1], value: value, suffix: m[3], comma: raw.indexOf(',') !== -1, decimals: (raw.split('.')[1] || '').length };
    }

    function format(n, info) {
        var s = info.decimals ? n.toFixed(info.decimals) : String(Math.round(n));
        if (info.comma) s = s.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        return info.prefix + s + info.suffix;
    }

    function countUp(el) {
        if (counted.has(el)) return;
        var original = el.textContent.trim();
        var info = parseNumber(original);
        if (!info) return;
        counted.set(el, original);
        var start = null, dur = Math.min(2200, 900 + info.value / 600);
        function step(ts) {
            if (!counted.has(el)) return;               // restored (edit mode)
            if (start === null) start = ts;
            var p = Math.min(1, (ts - start) / dur);
            var eased = 1 - Math.pow(1 - p, 3);
            el.textContent = format(info.value * eased, info);
            if (p < 1) requestAnimationFrame(step); else el.textContent = original;
        }
        el.textContent = format(0, info);
        requestAnimationFrame(step);
    }

    /* ---------- reveal ---------- */
    function prepare() {
        var groups = new Map();
        document.querySelectorAll(REVEAL).forEach(function (el) {
            if (el.classList.contains('arfa-reveal')) return;
            if (el.closest('.wasm-auto-slider, .wasm-marquee-slider, .wasm-gallery-marquee-wrapper, .wasm-slider-clone')) return;
            if (el.closest('header, .o_header_standard, .arfa-lightbox')) return;
            el.classList.add('arfa-reveal');
            // stagger siblings that sit in the same parent
            var parent = el.parentElement;
            var n = groups.get(parent) || 0;
            groups.set(parent, n + 1);
            el.style.setProperty('--arfa-delay', Math.min(n, 8) * 80 + 'ms');
            if (el.classList.contains('arfa-pd-tile')) el.classList.add('arfa-reveal-zoom');
            if (el.classList.contains('arfa-pd-facts')) el.classList.add('arfa-reveal-side');
            io.observe(el);
        });
        document.querySelectorAll(COUNT).forEach(function (el) { io.observe(el); });
    }

    function onIntersect(entries) {
        entries.forEach(function (entry) {
            if (!entry.isIntersecting) return;
            var el = entry.target;
            if (el.matches(COUNT)) countUp(el);
            if (el.classList.contains('arfa-reveal')) el.classList.add('is-in');
            io.unobserve(el);
        });
    }

    function showEverything() {
        root.classList.remove('arfa-anim');
        document.querySelectorAll('.arfa-reveal').forEach(function (el) {
            el.classList.remove('arfa-reveal', 'arfa-reveal-zoom', 'arfa-reveal-side', 'is-in');
            el.style.removeProperty('--arfa-delay');
            if (!el.getAttribute('style')) el.removeAttribute('style');
        });
        document.querySelectorAll(COUNT).forEach(function (el) {
            if (counted.has(el)) { el.textContent = counted.get(el); counted.delete(el); }
        });
        if (io) io.disconnect();
    }

    function start() {
        if (reduce || isEditMode() || !('IntersectionObserver' in window)) return;
        root.classList.add('arfa-anim');
        io = new IntersectionObserver(onIntersect, { rootMargin: '0px 0px -8% 0px', threshold: 0.12 });
        prepare();
        // late content (sliders initialised after load)
        setTimeout(function () { if (!isEditMode()) prepare(); }, 1200);
    }

    /* ---------- gold text on dark backgrounds + broken images ---------- */
    function luminanceOf(el) {
        while (el && el !== document.documentElement) {
            var cs = getComputedStyle(el);
            if (cs.backgroundImage && cs.backgroundImage !== 'none') return null;   // photo / gradient: skip
            var m = cs.backgroundColor.match(/[\d.]+/g);
            if (m && (m[3] === undefined || +m[3] > 0.6)) {
                var c = m.slice(0, 3).map(function (v) { v = v / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
                return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
            }
            el = el.parentElement;
        }
        return 1;
    }
    function markGoldOnDark() {
        document.querySelectorAll('#wrap .text-warning').forEach(function (el) {
            var L = luminanceOf(el.parentElement);
            if (L !== null && L < 0.2) el.classList.add('arfa-on-dark');
        });
    }
    function hideBrokenImages() {
        document.querySelectorAll('#wrap img').forEach(function (img) {
            var mark = function () { if (img.naturalWidth === 0) img.classList.add('arfa-img-broken'); };
            if (img.complete) mark(); else img.addEventListener('error', mark, { once: true });
        });
    }

    /* form fill-time stamp for the anti-spam check */
    function stampForms() {
        var now = String(Date.now());
        document.querySelectorAll('input.arfa-form-ts').forEach(function (i) { if (!i.value) i.value = now; });
    }

    function boot() {
        stampForms();
        if (!isEditMode()) { markGoldOnDark(); hideBrokenImages(); }
        start();
        if (window.MutationObserver && document.body) {
            new MutationObserver(function () {
                if (isEditMode()) {
                    showEverything();
                    document.querySelectorAll('.arfa-on-dark').forEach(function (el) { el.classList.remove('arfa-on-dark'); });
                    document.querySelectorAll('.arfa-img-broken').forEach(function (el) { el.classList.remove('arfa-img-broken'); });
                }
            })
                .observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
