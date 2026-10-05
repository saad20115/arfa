/** @odoo-module **/

/**
 * Wasm Video Player
 *  - showcase video (.wasm-video-wrapper): play/pause toggle (event delegation, no inline
 *    onclick for CSP). It is lazy: preload="none" + poster in the markup, and it only starts
 *    (muted) once it scrolls into view; it pauses again when it leaves the viewport. A video
 *    the visitor paused by hand is not restarted automatically.
 *  - homepage hero background video (.wasm-hero-bg-video): honours prefers-reduced-motion
 *    (no autoplay, the poster stays visible and nothing more is downloaded).
 */

const reduceMotion = () => !!(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
const userPaused = new WeakSet();

function setPlaying(video, playing) {
    const wrapper = video.closest('.wasm-video-wrapper');
    const playBtn = wrapper ? wrapper.querySelector('.wasm-video-play-btn') : null;
    if (playBtn) {
        playBtn.classList.toggle('is-playing', playing);
    }
}

function playMuted(video) {
    video.muted = true;
    const p = video.play();
    if (p && p.catch) {
        p.catch(() => { /* autoplay refused: the play button stays available */ });
    }
}

function wasmToggleVideoPlay(wrapperEl) {
    const video = wrapperEl ? wrapperEl.querySelector('video') : document.getElementById('wasm_showcase_video');
    if (!video) return;
    if (video.paused || video.ended) {
        userPaused.delete(video);
        playMuted(video);
    } else {
        userPaused.add(video);
        video.pause();
    }
}

function setupShowcase() {
    document.querySelectorAll('.wasm-video-wrapper').forEach((wrapper) => {
        wrapper.addEventListener('click', (e) => {
            e.stopPropagation();
            e.preventDefault();
            wasmToggleVideoPlay(wrapper);
        });
    });

    const videos = Array.from(document.querySelectorAll('.wasm-video-wrapper video'));
    videos.forEach((video) => {
        video.addEventListener('play', () => setPlaying(video, true));
        video.addEventListener('pause', () => setPlaying(video, false));
        video.addEventListener('ended', () => setPlaying(video, false));
    });
    if (!videos.length || reduceMotion()) return;

    if (!('IntersectionObserver' in window)) {
        videos.forEach(playMuted);
        return;
    }
    const io = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            const video = entry.target;
            if (entry.isIntersecting) {
                if (video.paused && !userPaused.has(video)) {
                    playMuted(video);
                }
            } else if (!video.paused) {
                video.pause();
            }
        });
    }, { rootMargin: '200px 0px', threshold: 0.01 });
    videos.forEach((video) => io.observe(video));
}

function setupHeroVideo() {
    if (!reduceMotion()) return;
    document.querySelectorAll('video.wasm-hero-bg-video').forEach((video) => {
        video.removeAttribute('autoplay');
        video.autoplay = false;
        video.pause();
        video.preload = 'none';
        video.load(); // back to the poster, stop downloading
    });
}

const setupVideoListeners = () => {
    setupHeroVideo();
    setupShowcase();
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupVideoListeners);
} else {
    setupVideoListeners();
}
