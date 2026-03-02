/**
 * WITTGrp Browser Extension - Background Service Worker
 * v1.1 — Intercepts browser downloads and routes them to WITTGrp Desktop App.
 */

const WITTGRP_PORT = 9614;
const WITTGRP_URL = `http://127.0.0.1:${WITTGRP_PORT}`;

// ── File types to intercept ───────────────────────────────────────────────
const VIDEO_MIME_TYPES = [
    'video/mp4', 'video/webm', 'video/x-matroska', 'video/avi',
    'video/quicktime', 'video/x-flv', 'video/3gpp', 'video/ogg',
    'video/mpeg', 'video/x-msvideo', 'video/x-ms-wmv',
    'audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/flac',
    'application/octet-stream',
];

const INTERCEPT_EXTENSIONS = [
    // Video
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.ts', '.mpeg', '.mpg', '.3gp', '.m2ts',
    // Audio
    '.mp3', '.flac', '.aac', '.ogg', '.wav', '.m4a', '.opus', '.wma',
    // Archives
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso',
    // Apps/programs
    '.exe', '.msi', '.apk', '.dmg', '.deb', '.rpm', '.pkg',
    // Documents
    '.pdf', '.epub', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
];

// Storage for captured videos per tab
const capturedVideos = new Map(); // tabId -> [{url, filename, referer, size}]

// Per-tab: last known page URL (for referer)
const tabReferers = new Map();    // tabId -> url

// Settings key
const SETTING_INTERCEPT = 'interceptEnabled';

// ── Helpers ──────────────────────────────────────────────────────────────

function isInterceptableURL(url) {
    try {
        const pathname = new URL(url).pathname.toLowerCase();
        return INTERCEPT_EXTENSIONS.some(ext => pathname.endsWith(ext));
    } catch { return false; }
}

function filenameFromURL(url) {
    try {
        const pathname = new URL(url).pathname;
        const parts = pathname.split('/');
        for (let i = parts.length - 1; i >= 0; i--) {
            const part = decodeURIComponent(parts[i]);
            if (part && part.includes('.') && part.length < 200) return part;
        }
    } catch { }
    return '';
}

async function isInterceptEnabled() {
    return new Promise(resolve => {
        chrome.storage.sync.get({ [SETTING_INTERCEPT]: true }, result => {
            resolve(result[SETTING_INTERCEPT]);
        });
    });
}

async function sendToWITTGrp(url, filename, referer, extraHeaders = {}) {
    try {
        const resp = await fetch(`${WITTGRP_URL}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, filename, referer, headers: extraHeaders }),
        });
        if (resp.ok) {
            showNotification('Download sent to WITTGrp', filename || url.substring(0, 60));
            return true;
        }
    } catch (e) {
        console.warn('[WITTGrp] App not running:', e.message);
        showNotification('WITTGrp App not running! Start WITTGrp first.', null, true);
    }
    return false;
}

function showNotification(title, message, isError = false) {
    chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon48.png',
        title: isError ? '⚠ WITTGrp Error' : '⬇ WITTGrp Download',
        message: message || title,
        priority: isError ? 2 : 0,
    });
}

// ── Track page URL per tab (for referer) ─────────────────────────────────

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.url) tabReferers.set(tabId, changeInfo.url);
    else if (tab && tab.url) tabReferers.set(tabId, tab.url);
});

chrome.tabs.onRemoved.addListener(tabId => {
    tabReferers.delete(tabId);
    capturedVideos.delete(tabId);
});

// ── CORE: Download Interception ───────────────────────────────────────────
//
// When the user clicks ANY download button or link in the browser,
// Chrome fires chrome.downloads.onCreated. We:
//   1. Check if interception is enabled (user toggle)
//   2. Check if the file type should be intercepted
//   3. Cancel/erase the browser download immediately
//   4. Send the URL to WITTGrp Desktop App which shows the download dialog

chrome.downloads.onCreated.addListener(async (downloadItem) => {
    const url = downloadItem.url || downloadItem.finalUrl || '';
    if (!url || url.startsWith('blob:') || url.startsWith('data:')) return;

    // Check if interception is enabled
    const enabled = await isInterceptEnabled();
    if (!enabled) return;

    // Check if this file type should be intercepted
    const mimeMatch = downloadItem.mime &&
        VIDEO_MIME_TYPES.some(m => downloadItem.mime.startsWith(m));
    const extMatch = isInterceptableURL(url);

    if (!mimeMatch && !extMatch) return;

    console.log(`[WITTGrp] Intercepting download: ${url} (mime: ${downloadItem.mime})`);

    // Cancel and erase the browser's download (prevents "failed" entry in downloads list)
    try {
        await chrome.downloads.cancel(downloadItem.id);
        chrome.downloads.erase({ id: downloadItem.id });
    } catch (e) {
        console.warn('[WITTGrp] Cancel failed (may have already finished):', e.message);
    }

    // Get the page referer: prefer from download item, then tab tracker
    const referer = downloadItem.referrer ||
        downloadItem.initiator ||
        tabReferers.get(downloadItem.tabId) || '';

    // Extract filename
    const filename = filenameFromURL(url) || downloadItem.filename || '';

    // Send to WITTGrp — shows dialog in the desktop app
    await sendToWITTGrp(url, filename, referer);
});

// ── Web Request Interceptor (captures video URLs for popup badge) ─────────

chrome.webRequest.onHeadersReceived.addListener(
    (details) => {
        if (details.tabId < 0) return;
        const url = details.url;

        const ctHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-type'
        );
        const mimeType = ctHeader?.value?.split(';')[0]?.trim() || '';

        const cdHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-disposition'
        );
        const contentDisposition = cdHeader?.value || '';

        const clHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-length'
        );
        const size = parseInt(clHeader?.value || '0');

        const isVideoMime = VIDEO_MIME_TYPES.some(m => mimeType.startsWith(m));
        const isDownloadableExt = isInterceptableURL(url);
        const isAttachment = contentDisposition.toLowerCase().includes('attachment');

        if ((isVideoMime && size > 500000) || (isDownloadableExt && size > 100000) || isAttachment) {
            const filename = filenameFromURL(url) || extractFilenameFromCD(contentDisposition) || 'download';

            if (!capturedVideos.has(details.tabId)) {
                capturedVideos.set(details.tabId, []);
            }
            const list = capturedVideos.get(details.tabId);
            if (!list.find(v => v.url === url)) {
                list.push({ url, filename, size, mimeType, referer: details.initiator || '' });
                chrome.action.setBadgeText({ text: String(list.length), tabId: details.tabId });
                chrome.action.setBadgeBackgroundColor({ color: '#e94560', tabId: details.tabId });
            }
        }
    },
    { urls: ['<all_urls>'] },
    ['responseHeaders']
);

function extractFilenameFromCD(cd) {
    if (!cd) return '';
    const match = cd.match(/filename[*]?=(?:UTF-8'')?["']?([^"';\r\n]+)["']?/i);
    return match ? decodeURIComponent(match[1].trim()) : '';
}

// ── Context Menu ──────────────────────────────────────────────────────────

chrome.runtime.onInstalled.addListener(() => {
    chrome.contextMenus.create({
        id: 'idm_download_link',
        title: '⬇ Download with WITTGrp',
        contexts: ['link', 'video', 'audio', 'image'],
    });
    chrome.contextMenus.create({
        id: 'idm_download_page_video',
        title: '⬇ Download video on this page',
        contexts: ['page'],
    });
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'idm_download_link' && info.linkUrl) {
        sendToWITTGrp(info.linkUrl, filenameFromURL(info.linkUrl), tab?.url || '');
    } else if (info.menuItemId === 'idm_download_page_video') {
        chrome.tabs.sendMessage(tab.id, { action: 'find_videos' });
    }
});

// ── Message Handler ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === 'send_to_wittgrp' || msg.action === 'send_to_idm') {
        sendToWITTGrp(msg.url, msg.filename, msg.referer, msg.headers || {}).then(ok => {
            sendResponse({ ok });
        });
        return true;
    }

    if (msg.action === 'get_videos' && sender.tab) {
        const videos = capturedVideos.get(sender.tab.id) || [];
        sendResponse({ videos });
        return true;
    }

    if (msg.action === 'videos_found') {
        const videos = msg.videos || [];
        for (const v of videos) {
            sendToWITTGrp(v.url, v.filename, sender.tab?.url || '');
        }
    }

    // Settings read/write from popup
    if (msg.action === 'get_settings') {
        chrome.storage.sync.get({ [SETTING_INTERCEPT]: true }, result => {
            sendResponse(result);
        });
        return true;
    }

    if (msg.action === 'set_settings') {
        chrome.storage.sync.set(msg.settings, () => sendResponse({ ok: true }));
        return true;
    }
});
