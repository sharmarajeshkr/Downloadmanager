import urllib.parse
import urllib.request
from html.parser import HTMLParser
import threading
import certifi
import ssl

class SiteGrabberParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.assets = set()

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        url = None
        
        if tag == 'a' and 'href' in attrs_dict:
            url = attrs_dict['href']
        elif tag in ('img', 'script', 'iframe') and 'src' in attrs_dict:
            url = attrs_dict['src']
        elif tag == 'link' and 'href' in attrs_dict:
            url = attrs_dict['href']
        elif tag == 'source' and 'src' in attrs_dict:
            url = attrs_dict['src']
            
        if url:
            # Ignore data URIs or javascript links
            if url.startswith(('javascript:', 'data:', 'mailto:')):
                return
                
            # Make absolute
            full_url = urllib.parse.urljoin(self.base_url, url)
            
            # Clean off fragments
            full_url = full_url.split('#')[0]
            
            if full_url.startswith(('http://', 'https://')):
                self.assets.add(full_url)

class SiteGrabber:
    def __init__(self):
        # Create an unverified SSL context to avoid certificate errors on poorly configured sites
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def fetch_assets(self, url: str) -> list[str]:
        """Fetches the URL, parses HTML, and returns a unique list of asset URLs."""
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, context=self.ssl_context, timeout=15) as response:
                html_bytes = response.read()
                
                # Try UTF-8 first, fallback to whatever else
                try:
                    html_content = html_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    html_content = html_bytes.decode('latin-1', errors='replace')
                
                parser = SiteGrabberParser(url)
                parser.feed(html_content)
                
                return sorted(list(parser.assets))
                
        except Exception as e:
            raise Exception(f"Failed to fetch {url}: {str(e)}")
