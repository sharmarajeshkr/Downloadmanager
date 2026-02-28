"""
SQLite Database Layer - Persists download queue, history, and settings
"""
import sqlite3
import os
import json
import time
import threading
from typing import Optional, List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "idm.db")


class Database:
    _local = threading.local()

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    @property
    def conn(self):
        return self._get_conn()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS downloads (
                id          TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                filename    TEXT NOT NULL,
                filepath    TEXT NOT NULL,
                size        INTEGER DEFAULT 0,
                downloaded  INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'Queued',
                category    TEXT DEFAULT 'Other',
                connections INTEGER DEFAULT 8,
                speed_limit INTEGER DEFAULT 0,
                priority    INTEGER DEFAULT 1,
                added_at    REAL DEFAULT 0,
                started_at  REAL DEFAULT 0,
                completed_at REAL DEFAULT 0,
                error_msg   TEXT DEFAULT '',
                referer     TEXT DEFAULT '',
                extra_headers TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS categories (
                name        TEXT PRIMARY KEY,
                extensions  TEXT NOT NULL,
                save_path   TEXT NOT NULL
            );
        """)
        # Insert default settings
        defaults = {
            'max_concurrent': '3',
            'default_connections': '8',
            'speed_limit': '0',
            'save_path': r'D:\idm\downloads\Other',
            'minimize_to_tray': 'true',
            'monitor_clipboard': 'true',
            'extension_server_port': '9614',
            'show_add_dialog': 'true',
            'theme': 'dark',
        }
        for k, v in defaults.items():
            conn.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)", (k, v))

        # Default categories
        cats = [
            ('Videos',    json.dumps(['mp4','mkv','avi','mov','wmv','flv','webm','m4v','ts','mpeg','mpg','3gp','vob','rmvb','divx']), r'D:\idm\downloads\Videos'),
            ('Music',     json.dumps(['mp3','flac','aac','ogg','wav','wma','m4a','opus','alac']), r'D:\idm\downloads\Music'),
            ('Documents', json.dumps(['pdf','doc','docx','xls','xlsx','ppt','pptx','txt','epub','odt','csv','rtf']), r'D:\idm\downloads\Documents'),
            ('Programs',  json.dumps(['exe','msi','dmg','pkg','deb','rpm','apk','iso','img']), r'D:\idm\downloads\Programs'),
            ('Archives',  json.dumps(['zip','rar','7z','tar','gz','bz2','xz','cab','tar.gz','tar.bz2']), r'D:\idm\downloads\Archives'),
            ('Other',     json.dumps([]),  r'D:\idm\downloads\Other'),
        ]
        for cat in cats:
            conn.execute("INSERT OR IGNORE INTO categories VALUES (?, ?, ?)", cat)
        conn.commit()
        conn.close()

    # ── Downloads CRUD ─────────────────────────────────────────────────────

    def add_download(self, task: Dict[str, Any]) -> bool:
        try:
            self.conn.execute("""
                INSERT OR REPLACE INTO downloads
                (id, url, filename, filepath, size, downloaded, status, category,
                 connections, speed_limit, priority, added_at, referer, extra_headers)
                VALUES (:id, :url, :filename, :filepath, :size, :downloaded, :status,
                        :category, :connections, :speed_limit, :priority, :added_at,
                        :referer, :extra_headers)
            """, {
                'id': task['id'],
                'url': task['url'],
                'filename': task['filename'],
                'filepath': task['filepath'],
                'size': task.get('size', 0),
                'downloaded': task.get('downloaded', 0),
                'status': task.get('status', 'Queued'),
                'category': task.get('category', 'Other'),
                'connections': task.get('connections', 8),
                'speed_limit': task.get('speed_limit', 0),
                'priority': task.get('priority', 1),
                'added_at': task.get('added_at', time.time()),
                'referer': task.get('referer', ''),
                'extra_headers': json.dumps(task.get('extra_headers', {})),
            })
            self.conn.commit()
            return True
        except Exception as e:
            return False

    def update_download(self, task_id: str, fields: Dict[str, Any]):
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [task_id]
        self.conn.execute(f"UPDATE downloads SET {sets} WHERE id = ?", vals)
        self.conn.commit()

    def get_download(self, task_id: str) -> Optional[Dict]:
        row = self.conn.execute("SELECT * FROM downloads WHERE id = ?", (task_id,)).fetchone()
        return dict(row) if row else None

    def get_all_downloads(self) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM downloads ORDER BY added_at DESC").fetchall()
        return [dict(r) for r in rows]

    def delete_download(self, task_id: str):
        self.conn.execute("DELETE FROM downloads WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_active_downloads(self) -> List[Dict]:
        rows = self.conn.execute(
            "SELECT * FROM downloads WHERE status IN ('Queued','Downloading','Paused') ORDER BY priority DESC, added_at ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Settings ───────────────────────────────────────────────────────────

    def get_setting(self, key: str, default: str = '') -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    def get_all_settings(self) -> Dict[str, str]:
        rows = self.conn.execute("SELECT key, value FROM settings").fetchall()
        return {r[0]: r[1] for r in rows}

    # ── Categories ─────────────────────────────────────────────────────────

    def get_categories(self) -> List[Dict]:
        rows = self.conn.execute("SELECT * FROM categories").fetchall()
        result = []
        for r in rows:
            result.append({
                'name': r['name'],
                'extensions': json.loads(r['extensions']),
                'save_path': r['save_path'],
            })
        return result

    def update_category(self, name: str, extensions: list, save_path: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO categories VALUES (?, ?, ?)",
            (name, json.dumps(extensions), save_path)
        )
        self.conn.commit()
