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

    // ── Inject Download Buttons on Video Elements ──────────────────────────

    function injectDownloadButtons() {
        document.querySelectorAll('video').forEach(video => {
            if (video.getAttribute(WITTGRP_ATTR)) return;
            video.setAttribute(WITTGRP_ATTR, '1');

            const btn = document.createElement('button');
            btn.textContent = '⬇ Download';
            btn.style.cssText = `
        position: absolute;
        top: 8px;
        right: 8px;
        z-index: 2147483647;
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

            // Prevent video players from pausing by catching all mouse/pointer events
            const stopAll = (e) => {
                e.preventDefault();
                e.stopPropagation();
            };
            btn.addEventListener('mousedown', stopAll);
            btn.addEventListener('mouseup', stopAll);
            btn.addEventListener('pointerdown', stopAll);
            btn.addEventListener('pointerup', stopAll);

            btn.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                let src = video.currentSrc || video.src;
                if (src && src.startsWith('blob:')) {
                    src = window.location.href;
                } else if (!src && window.location.hostname.includes('youtube')) {
                    src = window.location.href;
                }
                if (src) {
                    chrome.runtime.sendMessage({
                        action: 'send_to_wittgrp',
                        url: src,
                        filename: filenameFromURL(src) || 'video.mp4',
                        referer: location.href,
                    });
                    btn.textContent = '✓ Sent to WITTGrp';
                    btn.style.background = '#22c55e';
                    setTimeout(() => {
                        btn.textContent = '⬇ Download';
                        btn.style.background = '#e94560';
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

    // ── Link Interceptor - Add IDM button on file links ───────────────────

    function addDownloadLinksHandler() {
        const FILE_PATTERNS = /\.(mp4|mkv|avi|mov|wmv|flv|webm|mp3|flac|zip|rar|7z|exe|msi|pdf|doc|docx|iso|apk)([\?#]|$)/i;

        document.querySelectorAll('a[href]').forEach(link => {
            if (link.getAttribute(WITTGRP_ATTR)) return;
            if (!FILE_PATTERNS.test(link.href)) return;
            link.setAttribute(WITTGRP_ATTR, '1');

            const badge = document.createElement('span');
            badge.textContent = ' ⬇';
            badge.title = 'Click to download with IDM';
            badge.style.cssText = `
        color: #e94560;
        font-size: 12px;
        cursor: pointer;
        font-weight: 700;
        margin-left: 4px;
      `;
            badge.onclick = (e) => {
                e.preventDefault();
                e.stopPropagation();
                chrome.runtime.sendMessage({
                    action: 'send_to_wittgrp',
                    url: link.href,
                    filename: filenameFromURL(link.href),
                    referer: location.href,
                });
            };
            link.parentNode?.insertBefore(badge, link.nextSibling);
        });
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
        addDownloadLinksHandler();

        // Observe dynamic content
        const observer = new MutationObserver(() => {
            injectDownloadButtons();
            addDownloadLinksHandler();
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
