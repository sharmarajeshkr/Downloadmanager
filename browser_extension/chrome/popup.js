const WITTGRP_URL = 'http://127.0.0.1:9614';
let detectedVideos = [];

function formatSize(bytes) {
    if (!bytes) return '';
    const units = ['B', 'KB', 'MB', 'GB'];
    let i = 0;
    while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++; }
    return bytes.toFixed(1) + ' ' + units[i];
}

// Check IDM connection
async function checkIDM() {
    const dot = document.getElementById('status-dot');
    const text = document.getElementById('status-text');
    try {
        const resp = await fetch(WITTGRP_URL + '/ping', {
            method: 'POST', body: '{}',
            headers: { 'Content-Type': 'application/json' }
        });
        if (resp.ok) {
            dot.className = 'status-dot';
            text.textContent = 'WITTGrp Connected';
        } else throw new Error();
    } catch {
        dot.className = 'status-dot offline';
        text.textContent = 'WITTGrp Not Running';
    }
}

// Load videos detected by background script
function loadVideos() {
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
        if (!tabs[0]) return;

        // First ask background what it already knows
        chrome.runtime.sendMessage({ action: 'get_videos', tabId: tabs[0].id }, resp => {
            detectedVideos = resp?.videos || [];
            renderVideos();
        });

        // Then tell content script to scan for any DOM videos not yet detected
        chrome.tabs.sendMessage(tabs[0].id, { action: 'find_videos' }, () => {
            // Ignore errors if content script not loaded on this page
        });
    });
}

window.downloadVideo = function (index) {
    const v = detectedVideos[index];
    if (!v) return;
    chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
        chrome.runtime.sendMessage({
            action: 'send_to_wittgrp', url: v.url,
            filename: v.filename, referer: tabs[0]?.url || '',
        }, () => {
            const item = document.getElementById(`vi-${index}`);
            if (item) { item.style.borderColor = '#22c55e'; item.style.background = '#0d2018'; }
        });
    });
}

function renderVideos() {
    const container = document.getElementById('video-list');
    document.getElementById('video-count').textContent = detectedVideos.length;
    if (!detectedVideos.length) {
        container.innerHTML = `<div class="empty-state">
  <span class="empty-icon">🎬</span>
  <div>No media detected on this page.<br>Browse a video page and media will appear here.</div>
</div>`;
        return;
    }
    container.innerHTML = detectedVideos.map((v, i) => `
<div class="video-item" id="vi-${i}">
  <button class="btn-dl" data-idx="${i}">⬇ WITTGrp</button>
  <div class="video-name">${v.filename || 'video'}</div>
  <div class="video-meta">
    <span class="video-type">${v.mimeType || v.type || 'video'}</span>
    ${v.size ? '<span>' + formatSize(v.size) + '</span>' : ''}
  </div>
</div>
`).join('');

    // Attach listeners using event delegation or selection
    document.querySelectorAll('.btn-dl').forEach(btn => {
        btn.onclick = () => {
            const idx = btn.getAttribute('data-idx');
            window.downloadVideo(parseInt(idx, 10));
        };
    });
}

// For the regular download all button
window.downloadAll = function () {
    detectedVideos.forEach((_, i) => window.downloadVideo(i));
}

// Expose openIDM to the global window scope
window.openIDM = function () {
    alert('Please open IDM from your desktop or taskbar.');
}

// Auto-paste from clipboard on open
navigator.clipboard.readText().then(text => {
    if (text && (text.startsWith('http://') || text.startsWith('https://'))) {
        document.getElementById('url-input').value = text;
    }
}).catch(() => { });

document.addEventListener('DOMContentLoaded', () => {

    // Attach add-btn handler
    document.getElementById('add-btn').onclick = () => {
        const url = document.getElementById('url-input').value.trim();
        if (!url) return;
        chrome.tabs.query({ active: true, currentWindow: true }, tabs => {
            chrome.runtime.sendMessage({
                action: 'send_to_wittgrp', url, filename: '',
                referer: tabs[0]?.url || '',
            }, () => {
                document.getElementById('url-input').value = '';
                document.getElementById('add-btn').textContent = '✓ Sent!';
                setTimeout(() => document.getElementById('add-btn').textContent = '⬇ Send to WITTGrp', 2000);
            });
        });
    };

    // Also fix inline onClick in HTML by adding ID-based listener
    const dlAllBtn = document.getElementById('dl-all-btn');
    if (dlAllBtn) {
        dlAllBtn.onclick = window.downloadAll;
    }

    const openIdmBtn = document.querySelector('.open-idm');
    if (openIdmBtn) {
        openIdmBtn.onclick = window.openIDM;
    }

    // ── Intercept toggle ──────────────────────────────────────────────
    const interceptToggle = document.getElementById('intercept-toggle');

    // Load saved state
    chrome.runtime.sendMessage({ action: 'get_settings' }, result => {
        if (result && typeof result.interceptEnabled !== 'undefined') {
            interceptToggle.checked = result.interceptEnabled;
        }
    });

    // Save on change
    interceptToggle.addEventListener('change', () => {
        chrome.runtime.sendMessage({
            action: 'set_settings',
            settings: { interceptEnabled: interceptToggle.checked }
        });
    });

    checkIDM();
    // loadVideos();
    // setInterval(loadVideos, 3000);

});
