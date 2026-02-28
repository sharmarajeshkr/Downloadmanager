"""
Download Queue Manager - Controls concurrent downloads, priority, scheduling
"""
import uuid
import time
import threading
import logging
from typing import Optional, Dict, Callable, List
from .downloader import MultiThreadedDownloader, DownloadStatus
from .database import Database
from .file_manager import get_category, get_save_path, filename_from_url, probe_url

logger = logging.getLogger(__name__)


class DownloadTask:
    """Represents one download item in the queue."""

    def __init__(self, task_id: str, url: str, filename: str, filepath: str,
                 connections: int = 8, priority: int = 1, speed_limit: int = 0,
                 referer: str = '', extra_headers: dict = None, category: str = 'Other'):
        self.id = task_id
        self.url = url
        self.filename = filename
        self.filepath = filepath
        self.connections = connections
        self.priority = priority
        self.speed_limit = speed_limit
        self.referer = referer
        self.extra_headers = extra_headers or {}
        self.category = category

        self.status = DownloadStatus.QUEUED
        self.total_size = 0
        self.downloaded = 0
        self.speed = 0.0
        self.eta = 0
        self.error_msg = ''
        self.added_at = time.time()
        self.started_at = 0.0
        self.completed_at = 0.0

        self._downloader: Optional[MultiThreadedDownloader] = None
        self._thread: Optional[threading.Thread] = None


class QueueManager:
    """Manages the download queue with concurrency control."""

    def __init__(self, db: Database,
                 on_task_update: Optional[Callable] = None):
        self.db = db
        self.on_task_update = on_task_update  # fn(task: DownloadTask)
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.RLock()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    @property
    def max_concurrent(self) -> int:
        return int(self.db.get_setting('max_concurrent', '3'))

    @property
    def default_connections(self) -> int:
        return int(self.db.get_setting('default_connections', '8'))

    def _active_count(self) -> int:
        return sum(1 for t in self._tasks.values()
                   if t.status == DownloadStatus.DOWNLOADING)

    def load_from_db(self):
        """Load existing downloads from database on startup."""
        for row in self.db.get_all_downloads():
            task = DownloadTask(
                task_id=row['id'],
                url=row['url'],
                filename=row['filename'],
                filepath=row['filepath'],
                connections=row['connections'],
                priority=row['priority'],
                speed_limit=row['speed_limit'],
                referer=row['referer'],
                category=row['category'],
            )
            task.status = DownloadStatus(row['status'])
            task.total_size = row['size']
            task.downloaded = row['downloaded']
            task.added_at = row['added_at']
            task.error_msg = row['error_msg'] or ''
            # Reset stale "Downloading" to "Paused" (was interrupted)
            if task.status == DownloadStatus.DOWNLOADING:
                task.status = DownloadStatus.PAUSED
                self.db.update_download(task.id, {'status': 'Paused'})
            self._tasks[task.id] = task

    def add_download(self, url: str, filename: Optional[str] = None,
                     save_path: Optional[str] = None, connections: Optional[int] = None,
                     priority: int = 1, speed_limit: int = 0,
                     referer: str = '', extra_headers: dict = None,
                     auto_start: bool = True, size: int = 0, skip_probe: bool = False) -> str:
        """Add a new download to the queue. Returns task_id."""
        import json as _json
        task_id = str(uuid.uuid4())[:16]
        conn = connections or self.default_connections
        categories = self.db.get_categories()

        # Probe URL to get filename and size only if not explicitly skipped
        final_url = url
        if not skip_probe:
            final_url, probed_size, _, cd = probe_url(url, {'Referer': referer} if referer else None)
            fname = filename or filename_from_url(final_url, cd)
            size = size or probed_size
        else:
            fname = filename

        category = get_category(fname, categories)
        filepath = save_path or get_save_path(fname, category, categories)

        task = DownloadTask(
            task_id=task_id,
            url=final_url,
            filename=fname,
            filepath=filepath,
            connections=conn,
            priority=priority,
            speed_limit=speed_limit,
            referer=referer,
            extra_headers=extra_headers or {},
            category=category,
        )
        task.total_size = size

        with self._lock:
            self._tasks[task_id] = task

        self.db.add_download({
            'id': task_id, 'url': final_url, 'filename': fname,
            'filepath': filepath, 'size': size, 'downloaded': 0,
            'status': 'Queued', 'category': category,
            'connections': conn, 'speed_limit': speed_limit,
            'priority': priority, 'added_at': task.added_at,
            'referer': referer, 'extra_headers': _json.dumps(extra_headers or {}),
        })
        self._notify(task)

        if auto_start:
            self._try_start_next()

        return task_id

    def _try_start_next(self):
        """Start queued tasks if slots available."""
        with self._lock:
            active = self._active_count()
            if active >= self.max_concurrent:
                return
            # Sort by priority desc, then added_at asc
            queued = sorted(
                [t for t in self._tasks.values() if t.status == DownloadStatus.QUEUED],
                key=lambda t: (-t.priority, t.added_at)
            )
            for task in queued:
                if active >= self.max_concurrent:
                    break
                self._start_task(task)
                active += 1

    def _start_task(self, task: DownloadTask):
        """Launch download in a background thread."""
        task.started_at = time.time()

        def on_progress(downloaded, total, speed, eta):
            task.downloaded = downloaded
            task.total_size = total
            task.speed = speed
            task.eta = eta
            self._notify(task)

        def on_status(status: DownloadStatus):
            task.status = status
            if status == DownloadStatus.COMPLETED:
                task.completed_at = time.time()
                task.speed = 0
                task.eta = 0
                self.db.update_download(task.id, {
                    'status': 'Completed',
                    'downloaded': task.total_size,
                    'completed_at': task.completed_at,
                })
                self._try_start_next()  # Start next queued item
            elif status == DownloadStatus.ERROR:
                self.db.update_download(task.id, {'status': 'Error', 'error_msg': task.error_msg})
            elif status == DownloadStatus.PAUSED:
                self.db.update_download(task.id, {
                    'status': 'Paused', 'downloaded': task.downloaded,
                    'size': task.total_size,
                })
            self._notify(task)

        dl = MultiThreadedDownloader(
            task_id=task.id,
            url=task.url,
            filepath=task.filepath,
            connections=task.connections,
            headers={**task.extra_headers,
                     'Referer': task.referer} if task.referer else task.extra_headers,
            on_progress=on_progress,
            on_status_change=on_status,
            speed_limit_bytes=task.speed_limit,
        )
        task._downloader = dl
        task.status = DownloadStatus.DOWNLOADING
        self.db.update_download(task.id, {'status': 'Downloading', 'started_at': task.started_at})
        self._notify(task)

        def run():
            dl.start_download()

        t = threading.Thread(target=run, daemon=True)
        task._thread = t
        t.start()

    def pause(self, task_id: str):
        task = self._tasks.get(task_id)
        if task and task._downloader:
            task._downloader.pause()

    def resume(self, task_id: str):
        task = self._tasks.get(task_id)
        if not task:
            return
        if task.status == DownloadStatus.PAUSED:
            if task._downloader:
                # Resume existing downloader without spawning a duplicate master thread
                task.status = DownloadStatus.DOWNLOADING
                self.db.update_download(task.id, {'status': 'Downloading'})
                task._downloader.resume()
                self._notify(task)
            else:
                # Re-queue
                task.status = DownloadStatus.QUEUED
                self._try_start_next()

    def stop(self, task_id: str):
        task = self._tasks.get(task_id)
        if task and task._downloader:
            task._downloader.stop_and_save()
            task.status = DownloadStatus.STOPPED
            self.db.update_download(task.id, {'status': 'Stopped', 'downloaded': task.downloaded})
            self._notify(task)

    def remove(self, task_id: str, delete_file: bool = False):
        task = self._tasks.get(task_id)
        if not task:
            return
        if task._downloader:
            task._downloader.cancel()
        if delete_file:
            import os
            if os.path.exists(task.filepath):
                try:
                    os.remove(task.filepath)
                except Exception:
                    pass
        with self._lock:
            self._tasks.pop(task_id, None)
        self.db.delete_download(task_id)

    def start_all(self):
        for task in list(self._tasks.values()):
            if task.status in (DownloadStatus.QUEUED, DownloadStatus.PAUSED, DownloadStatus.STOPPED):
                task.status = DownloadStatus.QUEUED
        self._try_start_next()

    def stop_all(self):
        for task in list(self._tasks.values()):
            if task.status == DownloadStatus.DOWNLOADING:
                self.stop(task.id)

    def get_tasks(self) -> List[DownloadTask]:
        with self._lock:
            return list(self._tasks.values())

    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        return self._tasks.get(task_id)

    def _notify(self, task: DownloadTask):
        if self.on_task_update:
            try:
                self.on_task_update(task)
            except Exception:
                pass

    def _scheduler_loop(self):
        """Background loop to start queued items and update DB."""
        while True:
            time.sleep(2)
            self._try_start_next()
            # Persist progress for active downloads
            for task in list(self._tasks.values()):
                if task.status == DownloadStatus.DOWNLOADING:
                    self.db.update_download(task.id, {
                        'downloaded': task.downloaded,
                        'size': task.total_size,
                        'status': 'Downloading',
                    })
