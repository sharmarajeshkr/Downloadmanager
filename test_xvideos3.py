import requests, re

url = 'https://www.xvideos2.com/video.ohoutfk5c07/i_fuck_my_stepson_and_his_friend_while_they_watch_my_house'
try:
    html = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0 Safari/537.36'}, timeout=10, verify=False).text
    matches = re.findall(r"setVideoUrlHigh\('([^']+\.mp4[^']*)'\)", html)
    if not matches:
        matches = re.findall(r"(https?://[^\'\"]+\.mp4[^\'\"]*)", html)
    print("Matches found:")
    for m in matches:
        print(m)
except Exception as e:
    print(e)
