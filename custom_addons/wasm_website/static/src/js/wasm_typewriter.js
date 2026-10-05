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
        el.classList.remove('wasm-typewriter-on');
        el.innerHTML = s.originalHTML;
        state.delete(el);
    }

    function start(el) {
        if (state.has(el)) return;
        delete el.dataset.typewriterInitialized; // legacy flag saved by the old script
        var text = (el.getAttribute('data-typewriter-text') || el.textContent || '').trim();
        if (!text) return;
        // Long ALL-CAPS paragraphs (saved that way in older page copies) are hard to read:
        // show them in sentence case, keeping the company name in capitals.
        if (text.length > 40 && text === text.toUpperCase() && /[A-Z]/.test(text)) {
            text = text.toLowerCase()
                .replace(/(^\s*[a-z]|[.!?]\s+[a-z])/g, function (c) { return c.toUpperCase(); })
                .replace(/\bara?fa specialized systems\b/gi, 'ARFA Specialized Systems')
                .replace(/\bara?fa\b/gi, 'ARFA');
        }

        var s = { originalHTML: el.innerHTML, timer: null, stopped: false };
        state.set(el, s);

        // Layout-shift free: the whole sentence is always in the paragraph, so it keeps its final
        // size and every word is already on its final line. "Typing" only reveals words: the part
        // not typed yet is visibility:hidden, and the blinking cursor is the end border of the
        // typed part (no element moves). Screen readers get the full sentence once.
        var sr = document.createElement('span');
        sr.className = 'visually-hidden';
        sr.textContent = text;
        var content = document.createElement('span');
        content.className = 'wasm-typewriter-content wasm-typewriter-caret';
        content.setAttribute('aria-hidden', 'true');
        var rest = document.createElement('span');
        rest.className = 'wasm-typewriter-content wasm-typewriter-rest';
        rest.setAttribute('aria-hidden', 'true');
        el.innerHTML = '';
        el.classList.add('wasm-typewriter-on');
        el.appendChild(sr);
        el.appendChild(content);
        el.appendChild(rest);

        var words = text.split(/\s+/);
        function show(n) {
            content.textContent = words.slice(0, n).join(' ');
            rest.textContent = (n && n < words.length ? ' ' : '') + words.slice(n).join(' ');
        }
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            show(words.length); // no animation, just the sentence
            return;
        }

        var i = 0;
        show(0);
        function tick() {
            if (s.stopped) return;
            show(i);
            i++;
            if (i <= words.length) {
                s.timer = setTimeout(tick, 140);
            } else {
                s.timer = setTimeout(function () {
                    i = 0;
                    show(0);
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
