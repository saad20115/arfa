/** @odoo-module **/
/*
 * "Back to top" button with a gold scroll-progress ring.
 * Appears after the visitor scrolls a bit, shows how far down the page they
 * are, and scrolls smoothly back to the top. Built in JS and appended to
 * <body> (outside the editable page), so the Website Builder never saves it.
 */
(function () {
    'use strict';

    var R = 24, C = 2 * Math.PI * R;

    // The page may scroll on <html>, <body> (this theme: body has overflow:auto) or #wrapwrap.
    function scrollables() {
        var list = [], cands = [document.getElementById('wrapwrap'), document.body, document.scrollingElement || document.documentElement];
        cands.forEach(function (el) {
            if (!el || list.indexOf(el) !== -1) return;
            var oy = getComputedStyle(el).overflowY;
            var root = el === document.scrollingElement || el === document.documentElement;
            if (el.scrollHeight > el.clientHeight + 2 && (root || oy === 'auto' || oy === 'scroll')) list.push(el);
        });
        return list;
    }
    function scroller() {
        var list = scrollables();
        for (var i = 0; i < list.length; i++) { if (list[i].scrollTop > 0) return list[i]; }
        return list[0] || document.scrollingElement || document.documentElement;
    }
    function toTop() {
        scrollables().forEach(function (el) {
            if (el.scrollTo) { el.scrollTo({ top: 0, behavior: 'smooth' }); } else { el.scrollTop = 0; }
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function boot() {
        if (document.querySelector('.arfa-totop')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'arfa-totop';
        // label = backend text "layout.totop_aria", rendered on the floating buttons container
        var holder = document.querySelector('[data-totop-label]');
        btn.setAttribute('aria-label', (holder && holder.getAttribute('data-totop-label')) || 'Back to top');
        btn.innerHTML =
            '<svg class="arfa-totop-ring" viewBox="0 0 56 56" aria-hidden="true">' +
            '<circle class="arfa-totop-track" cx="28" cy="28" r="' + R + '"></circle>' +
            '<circle class="arfa-totop-progress" cx="28" cy="28" r="' + R + '" stroke-dasharray="' + C + '" stroke-dashoffset="' + C + '"></circle>' +
            '</svg>' +
            '<svg class="arfa-totop-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 15l6-6 6 6"></path></svg>';
        document.body.appendChild(btn);
        var ring = btn.querySelector('.arfa-totop-progress');
        var ticking = false;

        function update() {
            ticking = false;
            var el = scroller();
            var top = el.scrollTop || window.pageYOffset || 0;
            var max = Math.max(1, el.scrollHeight - el.clientHeight);
            var p = Math.min(1, Math.max(0, top / max));
            ring.setAttribute('stroke-dashoffset', String(C * (1 - p)));
            btn.classList.toggle('is-visible', top > 420);
        }
        function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(update); } }

        // capture phase: catches scrolling of <html>, <body> or #wrapwrap alike
        document.addEventListener('scroll', onScroll, { passive: true, capture: true });
        window.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll);
        // footer "Back to top" button(s) use the same smooth scroll
        document.addEventListener('click', function (ev) {
            var f = ev.target.closest && ev.target.closest('.arfa-footer-totop');
            if (!f) return;
            ev.preventDefault();
            toTop();
            var target = document.querySelector('header a, #wrapwrap a');
            if (target) setTimeout(function () { target.focus({ preventScroll: true }); }, 600);
        });
        btn.addEventListener('click', toTop);
        update();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
