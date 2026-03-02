/**
 * WITTGrp Content Script - Runs on every page
 * Finds video elements, streaming URLs, and injects download buttons
 */

(function () {
    'use strict';

    const WITTGRP_ATTR = 'data-idm-processed';

    // ── Find Videos in DOM ─────────────────────────────────────────────────

    function findVideos() {
        const found = [];
        const seen = new Set();

        // <video> elements
        document.querySelectorAll('video, video source').forEach(el => {
            const src = el.src || el.currentSrc || el.getAttribute('src');
            if (src && !seen.has(src) && src.startsWith('http')) {
                seen.add(src);
                found.push({
                    url: src,
                    filename: filenameFromURL(src) || 'video.mp4',
                    type: 'video_element',
                });
            }
            // Multiple sources
            el.querySelectorAll('source').forEach(s => {
                if (s.src && !seen.has(s.src)) {
                    seen.add(s.src);
                    found.push({ url: s.src, filename: filenameFromURL(s.src) || 'video.mp4' });
                }
            });
        });

        // <audio> elements
        document.querySelectorAll('audio, audio source').forEach(el => {
            const src = el.src || el.currentSrc;
            if (src && !seen.has(src) && src.startsWith('http')) {
                seen.add(src);
                found.push({ url: src, filename: filenameFromURL(src) || 'audio.mp3', type: 'audio_element' });
            }
        });

        // Check for HLS/DASH/m3u8 in page scripts
        const scripts = document.querySelectorAll('script:not([src])');
        scripts.forEach(s => {
            const text = s.textContent || '';
            const m3u8Matches = text.match(/https?:\/\/[^\s"']+\.m3u8[^\s"']*/g);
            if (m3u8Matches) {
                m3u8Matches.forEach(url => {
                    if (!seen.has(url)) {
                        seen.add(url);
                        found.push({ url, filename: 'm3u8_stream.m3u8', type: 'hls_stream' });
                    }
                });
            }
            const mpd = text.match(/https?:\/\/[^\s"']+\.mpd[^\s"']*/g);
            if (mpd) {
                mpd.forEach(url => {
                    if (!seen.has(url)) {
                        seen.add(url);
                        found.push({ url, filename: 'dash_stream.mpd', type: 'dash_stream' });
                    }
                });
            }
        });

        return found;
    }

    function filenameFromURL(url) {
        try {
            const pathname = new URL(url).pathname;
            const parts = pathname.split('/').filter(Boolean);
            for (let i = parts.length - 1; i >= 0; i--) {
                const p = decodeURIComponent(parts[i]);
                if (p.includes('.') && p.length < 200) return p;
            }
        } catch { }
        return '';
    }

    /**
     * Returns the cleanest possible URL for the current page's video.
     *
     * YouTube   → https://youtu.be/VIDEO_ID  (same as "Copy video URL" menu item)
     *              strips list=, start_radio=, index= params
     * Streaming → window.location.href
     * Other     → actual <video> src
     */
    function getCleanVideoURL(videoEl) {
        const hostname = window.location.hostname;

        // ---- YouTube: extract clean youtu.be short link ----
        if (hostname.includes('youtube.com') || hostname.includes('youtu.be')) {
            try {
                const params = new URLSearchParams(window.location.search);
                const videoId = params.get('v');
                if (videoId) {
                    // Exactly what YouTube "Copy video URL" produces
                    return `https://youtu.be/${videoId}`;
                }
            } catch (err) { console.warn('[WITTGrp] YT URL parse error:', err); }
            // Fallback: full page URL (e.g. youtu.be/ID?...)
            return window.location.href;
        }

        // ---- Other known streaming sites: send page URL ----
        const STREAMING_SITES = [
            'vimeo.com', 'dailymotion.com',
            'twitter.com', 'x.com',
            'facebook.com', 'instagram.com',
            'tiktok.com', 'twitch.tv',
            'xvideos.com', 'xhamster.com',
        ];
        if (STREAMING_SITES.some(d => hostname.includes(d))) {
            return window.location.href;
        }

        // ---- Regular sites: use actual video src ----
        if (videoEl) {
            const src = videoEl.currentSrc || videoEl.src;
            if (src && !src.startsWith('blob:') && src.startsWith('http')) {
                return src;
            }
        }
        return window.location.href; // final fallback
    }

    // ── Inject Download Buttons on Video Elements ──────────────────────────

    function injectDownloadButtons() {
        document.querySelectorAll('video').forEach(video => {
            if (video.getAttribute(WITTGRP_ATTR)) return;
            video.setAttribute(WITTGRP_ATTR, '1');

            const btn = document.createElement('button');
            btn.textContent = '⬇ Download';
            btn.style.cssText = `
        position: absolute;
        top: 50%;
        right: 8px;
        transform: translateY(-50%);
        z-index: 9999;
        background: #e94560;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: 700;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.4);
        font-family: 'Segoe UI', Arial, sans-serif;
        transition: background 0.2s;
      `;
            btn.onmouseover = () => btn.style.background = '#c73652';
            btn.onmouseout = () => btn.style.background = '#e94560';

            btn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();

                let src = getCleanVideoURL(video);

                if (src) {
                    const payload = {
                        action: 'send_to_wittgrp',
                        url: src,
                        filename: '',           // let the app detect it
                        referer: location.href,
                    };
                    console.log('[WITTGrp Extension] ⬇ Download button clicked!', payload);
                    chrome.runtime.sendMessage(payload);
                    btn.textContent = '✓ Sent to WITTGrp';
                    btn.style.background = '#22c55e';
                    setTimeout(() => {
                        btn.textContent = '⬇ Download';
                        btn.style.background = '#0A84FF';
                    }, 3000);
                }
            };

            // Position parent relatively if needed
            const parent = video.parentElement;
            if (parent) {
                const pos = getComputedStyle(parent).position;
                if (pos === 'static') parent.style.position = 'relative';
                parent.appendChild(btn);
            }
        });
    }

    // ── Global Link Interceptor ───────────────────────────────────────────
    // Intercepts all clicks on links matching file patterns to prevent 
    // the browser download system (and its popups) from ever starting.

    function setupGlobalInterceptor() {
        const FILE_PATTERNS = /\.(mp4|mkv|avi|mov|wmv|flv|webm|mp3|flac|zip|rar|7z|exe|msi|pdf|doc|docx|iso|apk)([\?#]|$)/i;

        document.addEventListener('click', (e) => {
            // Find the closest anchor tag
            const link = e.target.closest('a');
            if (!link || !link.href) return;

            // Only intercept if it matches a file extension we handle
            if (!FILE_PATTERNS.test(link.href)) return;

            // If it's a blobs/data URL, let browser handle it (usually small/generated)
            if (link.href.startsWith('blob:') || link.href.startsWith('data:')) return;

            console.log('[WITTGrp] Intercepted link click:', link.href);

            // STOP THE BROWSER from starting the download
            e.preventDefault();
            e.stopPropagation();

            // Send to WITTGrp
            chrome.runtime.sendMessage({
                action: 'send_to_wittgrp',
                url: link.href,
                filename: filenameFromURL(link.href),
                referer: location.href,
            });

            // Optional: visual feedback near the link
            showClickFeedback(e.clientX, e.clientY);
        }, true); // Use capture phase to intercept before site's own listeners
    }

    function showClickFeedback(x, y) {
        const div = document.createElement('div');
        div.textContent = '⬇ Sent to WITTGrp';
        div.style.cssText = `
            position: fixed;
            left: ${x + 10}px;
            top: ${y - 10}px;
            background: #22c55e;
            color: white;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
            z-index: 1000000;
            pointer-events: none;
            transition: opacity 1s, transform 1s;
        `;
        document.body.appendChild(div);
        setTimeout(() => {
            div.style.opacity = '0';
            div.style.transform = 'translateY(-20px)';
            setTimeout(() => div.remove(), 1000);
        }, 1000);
    }

    // ── Message Listener from Background ──────────────────────────────────

    chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
        if (msg.action === 'find_videos') {
            const videos = findVideos();
            chrome.runtime.sendMessage({ action: 'videos_found', videos });
        }
    });

    // ── Init ───────────────────────────────────────────────────────────────

    function init() {
        injectDownloadButtons();
        setupGlobalInterceptor();

        // Observe dynamic content for <video> injection
        const observer = new MutationObserver(() => {
            injectDownloadButtons();
        });
        observer.observe(document.body || document.documentElement, {
            childList: true,
            subtree: true,
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
