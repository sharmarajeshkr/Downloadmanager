"""
File Manager - Category detection, path management, duplicate handling
"""
import os
import json
import re
import urllib.parse
from typing import Optional, Tuple


EXTENSION_CATEGORIES = {
    'Videos':    ['mp4','mkv','avi','mov','wmv','flv','webm','m4v','ts','mpeg','mpg','3gp','vob','rmvb','divx','m2ts'],
    'Music':     ['mp3','flac','aac','ogg','wav','wma','m4a','opus','alac','aiff'],
    'Documents': ['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','epub','odt','csv','rtf','md'],
    'Programs':  ['exe','msi','dmg','pkg','deb','rpm','apk','iso','img','bin','run'],
    'Archives':  ['zip','rar','7z','tar','gz','bz2','xz','cab'],
}

BASE_DOWNLOAD_DIR = r'D:\idm\downloads'


def get_category(filename: str, custom_categories: Optional[list] = None) -> str:
    """Detect file category from extension."""
    ext = os.path.splitext(filename)[1].lstrip('.').lower()
    if custom_categories:
        for cat in custom_categories:
            if ext in [e.lower() for e in cat.get('extensions', [])]:
                return cat['name']
    for category, exts in EXTENSION_CATEGORIES.items():
        if ext in exts:
            return category
    return 'Other'


def get_save_path(filename: str, category: str, custom_categories: Optional[list] = None) -> str:
    """Get the full save path for a file."""
    if custom_categories:
        for cat in custom_categories:
            if cat['name'] == category and cat.get('save_path'):
                folder = cat['save_path']
                os.makedirs(folder, exist_ok=True)
                return ensure_unique(os.path.join(folder, filename))

    folder = os.path.join(BASE_DOWNLOAD_DIR, category)
    os.makedirs(folder, exist_ok=True)
    return ensure_unique(os.path.join(folder, filename))


def ensure_unique(filepath: str) -> str:
    """Append (1), (2), ... if file already exists."""
    if not os.path.exists(filepath):
        return filepath
    root, ext = os.path.splitext(filepath)
    counter = 1
    while os.path.exists(f"{root} ({counter}){ext}"):
        counter += 1
    return f"{root} ({counter}){ext}"


def filename_from_url(url: str, content_disposition: Optional[str] = None) -> str:
    """Extract filename from URL or Content-Disposition header."""
    # Try Content-Disposition first
    if content_disposition:
        # RFC 5987 encoded filename*=UTF-8''...
        match = re.search(r"filename\*=UTF-8''([^;\s]+)", content_disposition)
        if match:
            return urllib.parse.unquote(match.group(1))
        # Regular filename=
        match = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', content_disposition)
        if match:
            return match.group(1).strip().strip('"\'')

    # From URL path
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    name = os.path.basename(path.rstrip('/'))
    if name and '.' in name:
        return sanitize_filename(name)

    # Fallback
    return "download_" + str(int(os.times().elapsed))


def sanitize_filename(name: str) -> str:
    """Remove invalid chars for Windows filenames."""
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name)
    name = name.strip('. ')
    return name[:200] if name else "download"


def format_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes <= 0:
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_speed(speed_bps: float) -> str:
    """Human-readable download speed."""
    return format_size(int(speed_bps)) + "/s"


def format_eta(seconds: int) -> str:
    """Human-readable ETA."""
    if seconds <= 0:
        return "--:--"
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def probe_url(url: str, headers: dict = None) -> Tuple[str, int, bool, str]:
    """
    Returns (final_url, content_length, accepts_ranges, content_disposition)
    """
    import urllib.parse
    domain = urllib.parse.urlparse(url).netloc.lower()
    
    # Check if a known video domain or we suspect it's a webpage instead of a direct file
    import requests
    h = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WITTGrp/1.0'}
    if headers:
        h.update(headers)
        
    try:
        resp = requests.head(url, headers=h, allow_redirects=True, timeout=10, verify=False)
        final_url = resp.url
        size = int(resp.headers.get('Content-Length', 0))
        accepts = resp.headers.get('Accept-Ranges', '').lower() == 'bytes'
        cd = resp.headers.get('Content-Disposition', '')
        
        # If it's a direct file with a valid size, return it immediately
        if size > 0 and 'text/html' not in resp.headers.get('Content-Type', '').lower():
            return final_url, size, accepts, cd
            
    except Exception:
        pass

    # Fallback to yt-dlp to extract raw video links for generic pages (Youtube, Twitter, etc)
    try:
        import yt_dlp
        ydl_opts = {'format': 'best', 'noplaylist': True, 'quiet': True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            final_url = info.get('url', url)
            size = info.get('filesize') or info.get('filesize_approx') or 0
            title = info.get('title', 'video')
            ext = info.get('ext', 'mp4')
            
            cd = f'filename="{sanitize_filename(title)}.{ext}"'
            return final_url, int(size), True, cd
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"yt-dlp extraction failed: {e}")

    # Ultimate fallback
    return url, 0, False, ''
