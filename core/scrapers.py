"""
scrapers.py — Platform-specific URL probe/scraper classes.

Each class is responsible for one platform and exposes a single method:
    probe(url: str, headers: dict) -> (final_url, size, accepts_ranges, content_disposition)

The `probe_url()` dispatcher in file_manager.py selects the right class automatically.
"""

import re
import os
import logging
import urllib.parse
import urllib.request
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Return type alias
ProbeResult = Tuple[str, int, bool, str]

_CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _make_content_disposition(title: str, ext: str) -> str:
    """Build a safe Content-Disposition filename= string from a title."""
    # Strip emoji and non-ASCII characters (Windows filesystem + HTTP headers)
    title = title.encode("ascii", errors="ignore").decode("ascii")
    # Remove characters invalid in Windows filenames
    safe = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', title).strip('. ')
    # Collapse multiple spaces/underscores
    safe = re.sub(r'[_\s]{2,}', ' ', safe).strip()
    safe = safe[:120] if safe else "youtube_video"
    return f'filename="{safe}.{ext}"'


# ─────────────────────────────────────────────────────────────────────────────
# 1. Generic HTTP Scraper — direct file links (PDF, MP4, ZIP, etc.)
# ─────────────────────────────────────────────────────────────────────────────
class GenericHttpScraper:
    """
    Sends a HEAD request; returns result only if the server responds with
    a non-html Content-Type and a positive Content-Length.
    """

    NAME = "GenericHTTP"

    @staticmethod
    def matches(domain: str) -> bool:
        return True  # last-resort, always eligible, checked last

    def probe(self, url: str, headers: dict = None) -> Optional[ProbeResult]:
        import requests
        h = {"User-Agent": _CHROME_UA}
        if headers:
            h.update(headers)
        try:
            resp = requests.head(
                url, headers=h, allow_redirects=True, timeout=12, verify=False
            )
            ct = resp.headers.get("Content-Type", "").lower()
            size = int(resp.headers.get("Content-Length", 0))
            accepts = resp.headers.get("Accept-Ranges", "").lower() == "bytes"
            cd = resp.headers.get("Content-Disposition", "")

            if size > 0 and "text/html" not in ct:
                logger.info(f"[GenericHTTP] Direct file: {size} bytes, ct={ct!r}")
                # For YouTube CDN URLs (googlevideo.com), HEAD works but no Content-Disposition.
                # Extract size from the clen= query param which is always present in signed URLs.
                final_domain = urllib.parse.urlparse(resp.url).netloc.lower()
                if "googlevideo.com" in final_domain and not cd:
                    qs = urllib.parse.parse_qs(urllib.parse.urlparse(resp.url).query)
                    clen = int(qs.get("clen", [str(size)])[0])
                    cd = 'filename="youtube_video.mp4"'  # Placeholder; caller can override
                    logger.info(f"[GenericHTTP] YouTube CDN: clen={clen}")
                    return resp.url, clen or size, True, cd
                return resp.url, size, accepts, cd
        except Exception as e:
            logger.debug(f"[GenericHTTP] HEAD failed: {e}")

        # For YouTube CDN URLs that fail HEAD, try extracting size from the clen= param in URL
        parsed_qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        if "googlevideo.com" in urllib.parse.urlparse(url).netloc.lower() and "clen" in parsed_qs:
            clen = int(parsed_qs["clen"][0])
            logger.info(f"[GenericHTTP] YouTube CDN fallback via clen param: {clen}")
            return url, clen, True, 'filename="youtube_video.mp4"'

        return None


# ─────────────────────────────────────────────────────────────────────────────
# 2. YouTube Scraper — via yt-dlp, strips playlist params
# ─────────────────────────────────────────────────────────────────────────────
class YouTubeScraper:
    """
    Handles youtube.com and youtu.be URLs.
    Always extracts a SINGLE video regardless of playlist params.
    Returns the best available mp4/webm stream URL with the real video title.
    """

    NAME = "YouTube"
    _DOMAINS = ("youtube.com", "youtu.be", "www.youtube.com", "m.youtube.com")

    @staticmethod
    def matches(domain: str) -> bool:
        return any(d in domain for d in YouTubeScraper._DOMAINS)

    @staticmethod
    def _strip_playlist(url: str) -> str:
        """Remove list= and start_radio= params so yt-dlp extracts a single video."""
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        # Keep only the video ID param
        qs.pop("list", None)
        qs.pop("start_radio", None)
        qs.pop("index", None)
        new_query = urllib.parse.urlencode(
            {k: v[0] for k, v in qs.items()}, quote_via=urllib.parse.quote
        )
        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    @staticmethod
    def _build_ydl_opts(fmt: str, browser: Optional[str] = None) -> dict:
        opts = {
            "format": fmt,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "retries": 3,
            "extractor_retries": 2,
            "http_headers": {
                "User-Agent": _CHROME_UA,
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            },
        }
        if browser:
            opts["cookiesfrombrowser"] = (browser,)
        return opts

    def probe(self, url: str, headers: dict = None) -> Optional[ProbeResult]:
        try:
            import yt_dlp
        except ImportError:
            logger.error("[YouTube] yt-dlp not installed")
            return None

        clean_url = self._strip_playlist(url)
        logger.info(f"[YouTube] Probing (clean): {clean_url}")

        # Three format tiers — try each until one gives a usable direct URL
        FORMAT_CHAIN = [
            "best[ext=mp4]",               # Tier 1: pre-merged mp4 (fastest, single URL)
            "best",                         # Tier 2: best available single stream
            "bestvideo[ext=mp4]+bestaudio", # Tier 3: separate video+audio (biggest)
        ]

        browsers_to_try = [None, "edge", "chrome", "firefox", "brave", "opera", "safari"]

        for browser in browsers_to_try:
            sign_in_required = False
            for fmt in FORMAT_CHAIN:
                try:
                    opts = self._build_ydl_opts(fmt, browser=browser)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(clean_url, download=False)

                    # Pull title from info dict first
                    title = (
                        info.get("title")
                        or info.get("fulltitle")
                        or info.get("id")
                        or "youtube_video"
                    )
                    ext = info.get("ext") or "mp4"

                    # Pick the best downloadable URL
                    final_url = info.get("url")  # present for single-stream formats
                    if not final_url:
                        # Merged / requested_formats path
                        fmts = info.get("requested_formats") or info.get("formats") or []
                        # Prefer the video format (largest stream)
                        video_fmts = [f for f in fmts if f.get("vcodec", "none") != "none"]
                        if video_fmts:
                            final_url = video_fmts[0].get("url")
                            ext = video_fmts[0].get("ext") or ext

                    if not final_url:
                        logger.warning(f"[YouTube] Format {fmt!r}: no URL in info — trying next")
                        continue

                    # Aggregate file size
                    size = (
                        info.get("filesize")
                        or info.get("filesize_approx")
                        or sum(
                            (f.get("filesize") or f.get("filesize_approx") or 0)
                            for f in info.get("requested_formats") or []
                        )
                        or 0
                    )

                    cd = _make_content_disposition(title, ext)
                    logger.info(
                        f"[YouTube] OK (fmt={fmt!r} browser={browser}) — title={title!r} size={size} ext={ext}"
                    )
                    return final_url, int(size), True, cd

                except Exception as e:
                    err_msg = str(e).lower()
                    logger.warning(f"[YouTube] Format {fmt!r} failed (browser={browser}): {e}")
                    # If youtube demands a sign in because of bot detection or age restriction
                    if "sign in" in err_msg or "bot" in err_msg or "cookies" in err_msg:
                        sign_in_required = True
                        break # Stop trying other formats for this browser, try next browser
                    continue
            
            # If no sign-in or bot error occurred, no need to fallback to other browsers
            if not sign_in_required:
                break

        logger.error(f"[YouTube] All format tiers exhausted for {clean_url}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Generic yt-dlp Scraper — Twitter, Facebook, Instagram, Vimeo, etc.
# ─────────────────────────────────────────────────────────────────────────────
class YtDlpScraper:
    """
    Generic yt-dlp scraper for sites supported by yt-dlp but needing
    no special handling — e.g., Twitter/X, Facebook, Vimeo, Dailymotion.
    """

    NAME = "yt-dlp Generic"
    _DOMAINS = (
        "twitter.com", "x.com", "t.co",
        "facebook.com", "fb.com", "fb.watch",
        "instagram.com",
        "vimeo.com",
        "dailymotion.com",
        "tiktok.com",
        "reddit.com", "v.redd.it",
        "twitch.tv",
    )

    @staticmethod
    def matches(domain: str) -> bool:
        return any(d in domain for d in YtDlpScraper._DOMAINS)

    def probe(self, url: str, headers: dict = None) -> Optional[ProbeResult]:
        try:
            import yt_dlp
        except ImportError:
            logger.error("[yt-dlp] not installed")
            return None

        logger.info(f"[yt-dlp Generic] Probing: {url}")
        ydl_opts = {
            "format": "best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "socket_timeout": 30,
            "retries": 3,
            "http_headers": {
                "User-Agent": _CHROME_UA,
                "Accept-Language": "en-US,en;q=0.9",
            },
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            final_url = info.get("url", url)
            size = info.get("filesize") or info.get("filesize_approx") or 0
            title = info.get("title") or "video"
            ext = info.get("ext") or "mp4"
            cd = _make_content_disposition(title, ext)

            logger.info(f"[yt-dlp Generic] OK — title={title!r} size={size}")
            return final_url, int(size), True, cd
        except Exception as e:
            logger.error(f"[yt-dlp Generic] extraction failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# 4. XVideos Scraper — DOM regex (bypasses ISP/Cloudflare blocks)
# ─────────────────────────────────────────────────────────────────────────────
class XVideosScraper:
    """
    Fetches the XVideos page HTML via urllib (avoids requests TLS fingerprinting)
    and extracts the highest quality .mp4 URL via regex.
    Also extracts the real video title from the <title> tag.
    """

    NAME = "XVideos"

    @staticmethod
    def matches(domain: str) -> bool:
        return "xvideos" in domain

    def probe(self, url: str, headers: dict = None) -> Optional[ProbeResult]:
        import requests
        logger.info(f"[XVideos] Probing: {url}")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": _CHROME_UA, "Accept-Language": "en-US,en;q=0.9"}
            )
            html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")

            # -- Extract real title from <title> tag
            title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
            page_title = ""
            if title_match:
                raw_title = title_match.group(1).strip()
                # Remove trailing " - XVIDEOS.COM" suffix
                page_title = re.sub(r"\s*[-|]\s*XVIDEOS.*$", "", raw_title, flags=re.IGNORECASE).strip()

            # -- Extract video URL (high quality first, then generic mp4)
            matches = re.findall(r"setVideoUrlHigh\('([^']+\.mp4[^']*)'\)", html)
            if not matches:
                matches = re.findall(r"(https?://[^'\"]+\.mp4[^'\"]*)", html)
            if not matches:
                logger.warning("[XVideos] No mp4 URL found in page HTML")
                return None

            # Prefer 720p/1080p/high quality
            best_vid = sorted(
                set(matches),
                key=lambda x: ("1080p" in x) * 3 + ("720p" in x) * 2 + ("high" in x),
                reverse=True,
            )[0]

            # Measure real file size
            size = 0
            try:
                h = {"User-Agent": _CHROME_UA, "Referer": url}
                head_resp = requests.head(best_vid, headers=h, timeout=10, verify=False, allow_redirects=True)
                size = int(head_resp.headers.get("Content-Length", 0))
            except Exception:
                pass

            # Pass Referer to the downloader
            if headers is not None:
                headers["Referer"] = url

            if page_title:
                cd = _make_content_disposition(page_title, "mp4")
            else:
                cd = ""
            logger.info(f"[XVideos] OK — title={page_title!r} size={size}")
            return best_vid, size, True, cd

        except Exception as e:
            logger.error(f"[XVideos] scraper failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# 5. xHamster Scraper — DOM regex
# ─────────────────────────────────────────────────────────────────────────────
class XHamsterScraper:
    """
    Extracts .mp4 video URLs from xHamster pages via regex.
    Filters out thumbnail CDN URLs and HLS streams.
    Also extracts the real title from the <title> tag.
    """

    NAME = "xHamster"

    @staticmethod
    def matches(domain: str) -> bool:
        return "xhamster" in domain

    def probe(self, url: str, headers: dict = None) -> Optional[ProbeResult]:
        import requests
        logger.info(f"[xHamster] Probing: {url}")
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": _CHROME_UA, "Accept-Language": "en-US,en;q=0.9"}
            )
            html = urllib.request.urlopen(req, timeout=12).read().decode("utf-8", errors="ignore")

            # -- Extract title
            title_match = re.search(r"<title>([^<]+)</title>", html, re.IGNORECASE)
            page_title = ""
            if title_match:
                raw = title_match.group(1).strip()
                page_title = re.sub(r"\s*[-|]\s*xHamster.*$", "", raw, flags=re.IGNORECASE).strip()

            # -- Extract mp4 URLs; skip thumbnails and HLS
            all_mp4 = re.findall(r"(https?://[^'\"]+\.mp4[^'\"]*)", html)
            real_vids = [m for m in all_mp4 if "thumb" not in m and ".m3u8" not in m]
            if not real_vids:
                logger.warning("[xHamster] No mp4 URL found")
                return None

            best_vid = sorted(
                set(real_vids),
                key=lambda x: ("1080p" in x) * 3 + ("720p" in x) * 2 + ("480p" in x),
                reverse=True,
            )[0]

            size = 0
            try:
                h = {"User-Agent": _CHROME_UA, "Referer": url}
                head_resp = requests.head(best_vid, headers=h, timeout=10, verify=False, allow_redirects=True)
                size = int(head_resp.headers.get("Content-Length", 0))
            except Exception:
                pass

            if headers is not None:
                headers["Referer"] = url

            if page_title:
                cd = _make_content_disposition(page_title, "mp4")
            else:
                cd = ""
            logger.info(f"[xHamster] OK — title={page_title!r} size={size}")
            return best_vid, size, True, cd

        except Exception as e:
            logger.error(f"[xHamster] scraper failed: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Dispatcher — picks the right scraper for a URL
# ─────────────────────────────────────────────────────────────────────────────
# Priority order: most-specific first, GenericHTTP last
_SCRAPERS = [
    YouTubeScraper,
    XVideosScraper,
    XHamsterScraper,
    YtDlpScraper,     # Other yt-dlp supported sites
]

_GENERIC_HTTP = GenericHttpScraper()


def dispatch_probe(url: str, headers: dict = None) -> ProbeResult:
    """
    Main dispatcher. Tries GenericHTTP first for direct file URLs,
    then picks the appropriate platform scraper, then falls back to GenericHTTP.
    Returns (final_url, size, accepts_ranges, content_disposition).
    """
    domain = urllib.parse.urlparse(url).netloc.lower()

    # 1. Try direct HTTP HEAD first — fastest path for plain file URLs
    result = _GENERIC_HTTP.probe(url, headers)
    if result:
        return result

    # 2. Pick platform-specific scraper
    for scraper_cls in _SCRAPERS:
        if scraper_cls.matches(domain):
            scraper = scraper_cls()
            result = scraper.probe(url, headers)
            if result:
                return result
            # If the matched scraper failed, don't fall through to other platform scrapers
            break

    # 3. Ultimate fallback — return URL as-is with unknown size
    logger.warning(f"[dispatch_probe] All scrapers failed for {url}")
    return url, 0, False, ""
