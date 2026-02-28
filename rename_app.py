import os
import re

def replace_in_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = content
    for old, new in replacements:
        new_content = re.sub(old, new, new_content, flags=re.IGNORECASE if "(?i)" in old else 0)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated: {filepath}")

# Specific replacements mapped to files
replacements_map = {
    'main.py': [
        (r'IDM - Internet Download Manager', 'WITTGrp Download Manager'),
        (r'app\.setApplicationName\("IDM"\)', 'app.setApplicationName("WITTGrp Download Manage")'),
        (r'app\.setOrganizationName\("IDM"\)', 'app.setOrganizationName("WITTGrp")'),
        (r'logger = logging\.getLogger\(\'IDM\'\)', "logger = logging.getLogger('WITTGrp')"),
        (r'drawText\(110, 95, "IDM"\)', 'drawText(110, 95, "WITTGrp")'),
        (r'drawText\(110, 120, "Internet Download Manager"\)', 'drawText(110, 120, "WITTGrp Download Manage")'),
        (r'logger\.info\("IDM started successfully"\)', 'logger.info("WITTGrp started successfully")'),
    ],
    r'ui\main_window.py': [
        (r'IDM - Internet Download Manager', 'WITTGrp Download Manager'),
        (r'logo = QLabel\("⬇ IDM"\)', 'logo = QLabel("⬇ WITTGrp")'),
        (r'tray_menu\.addAction\("Show IDM",', 'tray_menu.addAction("Show WITTGrp",'),
        (r'tray_icon\.showMessage\("IDM', 'tray_icon.showMessage("WITTGrp'),
        (r'send them to IDM', 'send them to WITTGrp Download Manager'),
        (r'IDM - Download Started', 'WITTGrp - Download Started'),
        (r'IDM\)', 'WITTGrp)'),
        (r'Internet Download Manager', 'WITTGrp Download Manage'),
    ],
    r'ui\settings_dialog.py': [
        (r'IDM Settings & Preferences', 'WITTGrp Settings & Preferences'),
        (r'Start IDM with Windows', 'Start WITTGrp with Windows'),
    ],
    r'ui\stylesheet.py': [
        (r'IDM-style', 'WITTGrp-style'),
        (r'IDM-inspired', 'WITTGrp-inspired'),
    ],
    r'browser_extension\chrome\manifest.json': [
        (r'IDM Integration - Download Manager', 'WITTGrp Download Manage Integration'),
        (r'IDM Desktop App', 'WITTGrp Desktop App'),
        (r'IDM Downloader', 'WITTGrp Downloader'),
    ],
    r'browser_extension\chrome\popup.html': [
        (r'IDM Downloader', 'WITTGrp Downloader'),
        (r'Internet Download Manager Extension', 'WITTGrp Download Manage Extension'),
        (r'Send to IDM', 'Send to WITTGrp'),
        (r'Checking IDM…', 'Checking WITTGrp…'),
        (r'IDM Connected', 'WITTGrp Connected'),
        (r'IDM Not Running', 'WITTGrp Not Running'),
        (r'Open IDM App →', 'Open WITTGrp App →'),
        (r'IDM_URL', 'WITTGRP_URL'),
        (r'⬇ IDM', '⬇ WITTGrp'),
    ],
    r'browser_extension\chrome\background.js': [
        (r'IDM Browser Extension', 'WITTGrp Browser Extension'),
        (r'IDM desktop application', 'WITTGrp desktop application'),
        (r'IDM_PORT', 'WITTGRP_PORT'),
        (r'IDM_URL', 'WITTGRP_URL'),
        (r'sendToIDM', 'sendToWITTGrp'),
        (r'Download sent to IDM', 'Download sent to WITTGrp'),
        (r'IDM App not running!', 'WITTGrp App not running!'),
        (r'start IDM first', 'start WITTGrp first'),
        (r'⚠ IDM Error', '⚠ WITTGrp Error'),
        (r'⬇ IDM Download', '⬇ WITTGrp Download'),
        (r'Download with IDM', 'Download with WITTGrp'),
    ],
    r'browser_extension\chrome\content.js': [
        (r'IDM Content Script', 'WITTGrp Content Script'),
        (r'IDM_ATTR', 'WITTGRP_ATTR'),
        (r'send_to_idm', 'send_to_wittgrp'),
        (r'Sent to IDM', 'Sent to WITTGrp'),
        (r'Download with IDM', 'Download with WITTGrp'),
    ],
    r'core\downloader.py': [
        (r'IDM/1\.0', 'WITTGrp/1.0'),
    ],
    r'core\file_manager.py': [
        (r'IDM/1\.0', 'WITTGrp/1.0'),
    ]
}

base_dir = r'd:\idm'
for rel_path, replacements in replacements_map.items():
    file_path = os.path.join(base_dir, rel_path)
    if os.path.exists(file_path):
        replace_in_file(file_path, replacements)
    else:
        print(f"Not found: {file_path}")

print("Done renaming.")
