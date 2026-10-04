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

    function scroller() {
        var w = document.getElementById('wrapwrap');
        if (w && w.scrollHeight > w.clientHeight + 2 && getComputedStyle(w).overflowY !== 'visible') return w;
        return document.scrollingElement || document.documentElement;
    }

    function boot() {
        if (document.querySelector('.arfa-totop')) return;
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'arfa-totop';
        btn.setAttribute('aria-label', document.documentElement.lang && document.documentElement.lang.indexOf('ar') === 0 ? 'العودة للأعلى' : 'Back to top');
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

        window.addEventListener('scroll', onScroll, { passive: true });
        var w = document.getElementById('wrapwrap');
        if (w) w.addEventListener('scroll', onScroll, { passive: true });
        window.addEventListener('resize', onScroll);
        btn.addEventListener('click', function () {
            var el = scroller();
            if (el.scrollTo) { el.scrollTo({ top: 0, behavior: 'smooth' }); } else { el.scrollTop = 0; }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
        update();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
