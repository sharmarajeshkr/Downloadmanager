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

# Base download directory: user's Downloads folder / WITTGrp
# Respect the setting from DB if available, otherwise use OS default
_USER_DOWNLOADS = os.path.join(os.path.expanduser('~'), 'Downloads', 'WITTGrp')
BASE_DOWNLOAD_DIR = _USER_DOWNLOADS


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


def _is_generic_name(name: str) -> bool:
    """Check if a filename is too generic (e.g., 480p.mp4, video.mp4, index.html)."""
    if not name:
        return True
    name_lower = name.lower()
    base = os.path.splitext(name_lower)[0]
    
    # Common generic bases
    if base in ('download', 'video', 'videoplayback', 'playlist', 'media', 'file', 'index', 'master', 'stream'):
        return True
        
    # Resolution patterns like 480p, 720p, 1080p, 480p.h264
    if re.search(r'^\d{3,4}p(\.h264|\.x264|\.avc)?$', base):
        return True
        
    # Extremely short names or long hashes (MD5, UUIDs)
    if len(base) <= 4:
        return True
    
    # Check for long hashes (no spaces, no hyphens, or looks like UUID)
    if len(base) >= 32:
        # If it contains hyphens and words, it's likely a title slug, not a hash
        if '-' in base and not re.match(r'^[0-9a-fA-F-]+$', base):
            pass # Keep slugified titles
        elif re.match(r'^[0-9a-fA-F]{32,}$', base): # MD5/SHA
            return True
            
    return False

def filename_from_url(url: str, content_disposition: Optional[str] = None, referer: str = None) -> str:
    """Extract filename from URL, Content-Disposition header, or Referer."""
    # Try Content-Disposition first
    if content_disposition:
        match = re.search(r"filename\*=UTF-8''([^;\s]+)", content_disposition)
        if match:
            return urllib.parse.unquote(match.group(1))
        match = re.search(r'filename=["\']?([^"\';\r\n]+)["\']?', content_disposition)
        if match:
            return match.group(1).strip().strip('"\'')

    # Parse URL path
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    url_name = os.path.basename(path.rstrip('/'))
    
    ext = os.path.splitext(url_name)[1] if '.' in url_name else ''
    url_is_generic = _is_generic_name(url_name)
    
    # Try to extract a better filename from the Referer URL
    if referer:
        ref_parsed = urllib.parse.urlparse(referer)
        ref_path = urllib.parse.unquote(ref_parsed.path)
        ref_name = os.path.basename(ref_path.rstrip('/'))
        
        # Avoid generic page names
        if ref_name and not ref_name.endswith(('.html', '.htm', '.php', '.asp', '.aspx')):
            # Strip common tube site IDs at the end (e.g. ...-xh2Aj6r)
            ref_name = re.sub(r'-[a-zA-Z0-9]{5,15}$', '', ref_name)
            
            # If the referer has a good name, prioritize it over a generic URL name
            if not _is_generic_name(ref_name):
                # If referer lacks extension, append the one from the URL (or a default)
                if '.' not in ref_name:
                    ref_name += (ext if ext else '.mp4')
                    
                sanitized = sanitize_filename(ref_name)
                if sanitized:
                    return sanitized

    # If the URL path has a good filename with an extension, use it
    if url_name and '.' in url_name and not url_is_generic:
        return sanitize_filename(url_name)
        
    # If standard URL path is bad, try the URL query parameters
    query_params = urllib.parse.parse_qs(parsed.query)
    for k, v in query_params.items():
        if any(v_item and '.' in v_item for v_item in v):
            for v_item in v:
                if '.' in v_item and not _is_generic_name(v_item):
                    return sanitize_filename(v_item)

    # General fallback: return generic URL name if it has an extension, else sanitized fallback
    if url_name and '.' in url_name:
        return sanitize_filename(url_name)
        
    fallback_name = url_name if url_name else parsed.netloc
    if fallback_name:
        sanitized = sanitize_filename(fallback_name)
        if sanitized:
            return sanitized

    return "download"


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
    Returns (final_url, content_length, accepts_ranges, content_disposition).
    Delegates to the appropriate platform scraper in core/scrapers.py.
    """
    from core.scrapers import dispatch_probe
    return dispatch_probe(url, headers)
