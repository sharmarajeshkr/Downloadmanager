import re

try:
    with open('idm_xvideos.html', 'r', encoding='utf-8') as f:
        html = f.write()
except:
    with open('idm_xvideos.html', 'r', encoding='utf-8') as f:
        html = f.read()

# XVideos stores mp4 links in HTML5 variables 
matches = re.findall(r"html5player\.setVideoUrl\w*\('([^']+)'\)", html)
if not matches:
    # try just finding any mp4
    matches = re.findall(r"(https?://[^\'\"]+\.mp4)", html)

for m in set(matches):
    print(m)
