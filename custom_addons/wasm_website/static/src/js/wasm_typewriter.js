/** @odoo-module **/
/*
 * Typewriter effect for the hero lead text.
 * The original markup is never destroyed for good: it is kept in memory and
 * restored as soon as the Website Builder enters edit mode, so the editor never
 * saves an empty / half-typed paragraph (which is what the old version did).
 */
(function () {
    'use strict';

    var state = new WeakMap();

    function isEditMode() {
        var body = document.body;
        return !!(body && (body.classList.contains('editor_enable') ||
            body.classList.contains('o_edit_mode') ||
            /[?&]enable_editor=1/.test(window.location.search)));
    }

    function stop(el) {
        var s = state.get(el);
        if (!s) return;
        clearTimeout(s.timer);
        s.stopped = true;
        el.innerHTML = s.originalHTML;
        state.delete(el);
    }

    function start(el) {
        if (state.has(el)) return;
        delete el.dataset.typewriterInitialized; // legacy flag saved by the old script
        var text = (el.getAttribute('data-typewriter-text') || el.textContent || '').trim();
        if (!text) return;

        var s = { originalHTML: el.innerHTML, timer: null, stopped: false };
        state.set(el, s);

        var content = document.createElement('span');
        content.className = 'wasm-typewriter-content';
        var cursor = document.createElement('span');
        cursor.className = 'wasm-typewriter-cursor';
        cursor.textContent = '|';
        el.innerHTML = '';
        el.appendChild(content);
        el.appendChild(cursor);

        var words = text.split(/\s+/);
        var i = 0;
        function tick() {
            if (s.stopped) return;
            content.textContent = words.slice(0, i).join(' ');
            i++;
            if (i <= words.length) {
                s.timer = setTimeout(tick, 140);
            } else {
                s.timer = setTimeout(function () {
                    i = 0;
                    content.textContent = '';
                    s.timer = setTimeout(tick, 400);
                }, 4000);
            }
        }
        s.timer = setTimeout(tick, 200);
    }

    function refresh() {
        var edit = isEditMode();
        document.querySelectorAll('.wasm-typewriter-target').forEach(function (el) {
            if (edit) { stop(el); } else { start(el); }
        });
    }

    function boot() {
        refresh();
        if (window.MutationObserver && document.body) {
            new MutationObserver(refresh).observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
