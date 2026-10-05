/** @odoo-module **/
/*
 * ARFA step sliders / marquees.
 *
 * Why this file was rewritten:
 *  The old version cloned slides into the DOM and flagged the slider with
 *  data-slider-initialized="true". When someone opened the Website Builder and
 *  pressed Save, those clones + the flag + the inline transform were saved into
 *  the page (a website-specific copy of the template). After that the slider
 *  stopped moving, module updates no longer reached the homepage, and every new
 *  save duplicated the clones again.
 *
 *  Now:
 *   - state is kept in JS memory (WeakMap), never in DOM attributes;
 *   - clones / flags already saved in a page are cleaned on load;
 *   - nothing runs while the Website Builder is in edit mode, and everything is
 *     reverted the moment edit mode starts, so the editor only saves clean HTML.
 */
(function () {
    'use strict';

    var SLIDER_SELECTOR = '.wasm-auto-slider, .wasm-marquee-slider, .wasm-gallery-marquee-wrapper';
    var TRACK_SELECTOR = '.wasm-slider-track, .wasm-marquee-track, .wasm-gallery-marquee-track';
    var GAP = 24;
    var STEP_MS = 2000;
    var running = new WeakMap();

    function isEditMode() {
        var body = document.body;
        return !!(body && (body.classList.contains('editor_enable') ||
            body.classList.contains('o_edit_mode') ||
            /[?&]enable_editor=1/.test(window.location.search)));
    }

    function isRTL() {
        return document.documentElement.dir === 'rtl' ||
            (document.body && document.body.classList.contains('o_rtl')) ||
            (document.documentElement.lang || '').indexOf('ar') === 0;
    }

    /* Remove anything an old script version may have baked into the saved page. */
    function cleanSlider(slider) {
        delete slider.dataset.sliderInitialized;
        var track = slider.querySelector(TRACK_SELECTOR);
        if (!track) return null;
        track.querySelectorAll('.wasm-slider-clone').forEach(function (c) { c.remove(); });
        track.style.removeProperty('transform');
        track.style.removeProperty('transition');
        if (!track.getAttribute('style')) track.removeAttribute('style');
        return track;
    }

    function stopSlider(slider) {
        var state = running.get(slider);
        if (state) {
            clearInterval(state.timer);
            window.removeEventListener('resize', state.onResize);
            slider.removeEventListener('mouseenter', state.onEnter);
            slider.removeEventListener('mouseleave', state.onLeave);
            running.delete(slider);
        }
        cleanSlider(slider);
    }

    function startSlider(slider) {
        if (running.has(slider)) return;
        var track = cleanSlider(slider);
        if (!track) return;

        var originals = Array.from(track.children);
        var count = originals.length;
        if (count <= 1) return;

        for (var round = 0; round < 2; round++) {
            for (var i = 0; i < count; i++) {
                var clone = originals[i].cloneNode(true);
                clone.classList.add('wasm-slider-clone');
                clone.setAttribute('aria-hidden', 'true');
                // decorative duplicates: keep them out of the tab order / accessibility tree
                clone.setAttribute('inert', '');
                clone.querySelectorAll('a, button, input, select, textarea, iframe, [tabindex]').forEach(function (f) {
                    f.setAttribute('tabindex', '-1');
                });
                if (clone.matches('a, button, [tabindex]')) clone.setAttribute('tabindex', '-1');
                track.appendChild(clone);
            }
        }

        var direction = slider.dataset.direction || 'left';
        var index = direction === 'right' ? count : 0;
        var paused = false;

        function place(animate) {
            var first = track.children[0];
            if (!first) return;
            var offset = index * (first.offsetWidth + GAP);
            track.style.transition = animate ? 'transform 0.6s cubic-bezier(0.25, 1, 0.5, 1)' : 'none';
            track.style.transform = 'translateX(' + (isRTL() ? offset : -offset) + 'px)';
        }

        function step() {
            if (paused || document.hidden) return;
            index += direction === 'right' ? -1 : 1;
            place(true);
            if (direction === 'right' && index <= 0) {
                setTimeout(function () { index = count; place(false); }, 600);
            } else if (direction !== 'right' && index >= count) {
                setTimeout(function () { index = 0; place(false); }, 600);
            }
        }

        var state = {
            timer: setInterval(step, parseInt(slider.dataset.autoInterval, 10) || STEP_MS),
            onResize: function () { place(false); },
            onEnter: function () { paused = true; },
            onLeave: function () { paused = false; },
        };
        window.addEventListener('resize', state.onResize);
        slider.addEventListener('mouseenter', state.onEnter);
        slider.addEventListener('mouseleave', state.onLeave);
        running.set(slider, state);
        place(false);
    }

    /*
     * Hero pillar cards (3 cards under the hero): on phones / small screens the
     * row is a horizontal scroll-snap strip. Move it automatically one card at a
     * time, like the sliders below. Native scrolling is used, so swiping by hand
     * still works; the auto-move pauses while the visitor touches or hovers it.
     */
    var PILLAR_ROW = '.wasm-hero-pillars-section .row';
    var SMALL_SCREEN = window.matchMedia ? window.matchMedia('(max-width: 991.98px)') : null;
    var pillarState = new WeakMap();

    function stopPillars(row) {
        var s = pillarState.get(row);
        if (!s) return;
        clearInterval(s.timer);
        ['touchstart', 'mouseenter'].forEach(function (ev) { row.removeEventListener(ev, s.pause); });
        ['touchend', 'mouseleave'].forEach(function (ev) { row.removeEventListener(ev, s.resume); });
        pillarState.delete(row);
    }

    function startPillars(row) {
        if (pillarState.has(row) || row.children.length <= 1) return;
        var s = { paused: false, resumeAt: 0 };
        s.pause = function () { s.paused = true; };
        s.resume = function () { s.paused = false; s.resumeAt = Date.now() + 2500; };
        s.timer = setInterval(function () {
            if (s.paused || document.hidden || Date.now() < s.resumeAt) return;
            var first = row.children[0];
            var gap = parseFloat(getComputedStyle(row).columnGap) || 16;
            var step = first.getBoundingClientRect().width + gap;
            var dir = isRTL() ? -1 : 1;
            var atEnd = Math.abs(row.scrollLeft) + row.clientWidth >= row.scrollWidth - 8;
            if (atEnd) {
                row.scrollTo({ left: 0, behavior: 'smooth' });
            } else {
                row.scrollBy({ left: dir * step, behavior: 'smooth' });
            }
        }, STEP_MS + 600);
        ['touchstart', 'mouseenter'].forEach(function (ev) { row.addEventListener(ev, s.pause, { passive: true }); });
        ['touchend', 'mouseleave'].forEach(function (ev) { row.addEventListener(ev, s.resume, { passive: true }); });
        pillarState.set(row, s);
    }

    function refreshPillars(edit) {
        var small = SMALL_SCREEN ? SMALL_SCREEN.matches : window.innerWidth < 992;
        document.querySelectorAll(PILLAR_ROW).forEach(function (row) {
            if (edit || !small) { stopPillars(row); } else { startPillars(row); }
        });
    }

    function refresh() {
        var edit = isEditMode();
        document.querySelectorAll(SLIDER_SELECTOR).forEach(function (s) {
            if (edit) { stopSlider(s); } else { startSlider(s); }
        });
        refreshPillars(edit);
    }

    function boot() {
        refresh();
        // React when the Website Builder toggles edit mode on this document.
        if (window.MutationObserver && document.body) {
            new MutationObserver(refresh).observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }
        if (SMALL_SCREEN) {
            var onChange = function () { refreshPillars(isEditMode()); };
            if (SMALL_SCREEN.addEventListener) { SMALL_SCREEN.addEventListener('change', onChange); } else { SMALL_SCREEN.addListener(onChange); }
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', boot, { once: true });
    } else {
        boot();
    }
})();
