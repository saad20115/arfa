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

    function refresh() {
        var edit = isEditMode();
        document.querySelectorAll(SLIDER_SELECTOR).forEach(function (s) {
            if (edit) { stopSlider(s); } else { startSlider(s); }
        });
    }

    function boot() {
        refresh();
        // React when the Website Builder toggles edit mode on this document.
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
