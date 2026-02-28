import urllib.request
import re

url = 'https://www.xvideos2.com/video.ohoutfk5c07/i_fuck_my_stepson_and_his_friend_while_they_watch_my_house'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) width=1000 Chrome/121.0.0.0 Safari/537.36'})

try:
    html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
    with open('idm_xvideos.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("HTML saved.")
except Exception as e:
    print(f"Error: {e}")
