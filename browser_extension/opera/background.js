/**
 * WITTGrp Browser Extension - Background Service Worker
 * Intercepts network requests to detect downloadable videos and files,
 * and relays them to the WITTGrp desktop application via localhost:9614
 */

const WITTGRP_PORT = 9614;
const WITTGRP_URL = `http://127.0.0.1:${WITTGRP_PORT}`;

// Video/audio MIME types to intercept
const VIDEO_MIME_TYPES = [
    'video/mp4', 'video/webm', 'video/x-matroska', 'video/avi',
    'video/quicktime', 'video/x-flv', 'video/3gpp', 'video/ogg',
    'video/mpeg', 'video/x-msvideo', 'video/x-ms-wmv',
    'audio/mpeg', 'audio/mp4', 'audio/ogg', 'audio/wav', 'audio/flac',
    'application/octet-stream',
];

// File extensions triggering IDM capture
const DOWNLOAD_EXTENSIONS = [
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mpeg', '.mpg',
    '.mp3', '.flac', '.aac', '.ogg', '.wav', '.m4a', '.opus',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.iso',
    '.exe', '.msi', '.apk', '.dmg', '.deb', '.rpm',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.epub',
];

// Storage for captured videos per tab
const capturedVideos = new Map(); // tabId -> [{url, filename, referer, size}]

// Check if URL is a downloadable file by extension
function isDownloadableURL(url) {
    try {
        const pathname = new URL(url).pathname.toLowerCase();
        return DOWNLOAD_EXTENSIONS.some(ext => pathname.endsWith(ext));
    } catch {
        return false;
    }
}

// Extract filename from URL
function filenameFromURL(url) {
    try {
        const pathname = new URL(url).pathname;
        const parts = pathname.split('/');
        for (let i = parts.length - 1; i >= 0; i--) {
            const part = decodeURIComponent(parts[i]);
            if (part && part.includes('.') && part.length < 200) {
                return part;
            }
        }
    } catch { }
    return '';
}

// Send download request to IDM desktop app
async function sendToWITTGrp(url, filename, referer, extraHeaders = {}) {
    try {
        const resp = await fetch(`${WITTGRP_URL}/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, filename, referer, headers: extraHeaders }),
        });
        if (resp.ok) {
            showNotification(`Download sent to WITTGrp: ${filename || url.substring(0, 60)}`);
            return true;
        }
    } catch (e) {
        console.warn('IDM not running:', e.message);
        showNotification('WITTGrp App not running! Please start WITTGrp first.', true);
    }
    return false;
}

function showNotification(message, isError = false) {
    chrome.notifications.create({
        type: 'basic',
        iconUrl: 'icon48.png',
        title: isError ? '⚠ WITTGrp Error' : '⬇ WITTGrp Download',
        message: message,
        priority: isError ? 2 : 0,
    });
}

// ── Web Request Interceptor ───────────────────────────────────────────────

chrome.webRequest.onHeadersReceived.addListener(
    (details) => {
        if (details.tabId < 0) return;
        const url = details.url;

        // Check Content-Type header
        const ctHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-type'
        );
        const mimeType = ctHeader?.value?.split(';')[0]?.trim() || '';

        // Get Content-Disposition (may have filename)
        const cdHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-disposition'
        );
        const contentDisposition = cdHeader?.value || '';

        // Get size
        const clHeader = details.responseHeaders?.find(
            h => h.name.toLowerCase() === 'content-length'
        );
        const size = parseInt(clHeader?.value || '0');

        // Detect if it's a video/download
        const isVideoMime = VIDEO_MIME_TYPES.some(m => mimeType.startsWith(m));
        const isDownloadableExt = isDownloadableURL(url);
        const isAttachment = contentDisposition.toLowerCase().includes('attachment');

        if ((isVideoMime && size > 500000) || (isDownloadableExt && size > 100000) || isAttachment) {
            const filename = filenameFromURL(url) || extractFilenameFromCD(contentDisposition) || 'download';

            // Store for popup display
            if (!capturedVideos.has(details.tabId)) {
                capturedVideos.set(details.tabId, []);
            }
            const list = capturedVideos.get(details.tabId);
            if (!list.find(v => v.url === url)) {
                list.push({
                    url, filename, size, mimeType,
                    referer: details.initiator || ''
                });
                // Update badge
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
        const filename = filenameFromURL(info.linkUrl);
        sendToWITTGrp(info.linkUrl, filename, tab?.url || '');
    } else if (info.menuItemId === 'idm_download_page_video') {
        // Ask content script to find video URLs
        chrome.tabs.sendMessage(tab.id, { action: 'find_videos' });
    }
});

// ── Message Handler ───────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    if (msg.action === 'send_to_wittgrp' || msg.action === 'send_to_idm') {
        sendToWITTGrp(msg.url, msg.filename, msg.referer, msg.headers || {}).then(ok => {
            sendResponse({ ok });
        });
        return true; // async
    }

    if (msg.action === 'get_videos' && sender.tab) {
        const videos = capturedVideos.get(sender.tab.id) || [];
        sendResponse({ videos });
        return true;
    }

    if (msg.action === 'videos_found') {
        // From content script - list of video src URLs found in DOM
        const videos = msg.videos || [];
        for (const v of videos) {
            sendToWITTGrp(v.url, v.filename, sender.tab?.url || '');
        }
    }
});

// Clean up on tab close
chrome.tabs.onRemoved.addListener((tabId) => {
    capturedVideos.delete(tabId);
});
