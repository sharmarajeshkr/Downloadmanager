"""
Core Download Engine - Multi-threaded chunked downloader with resume support
"""
import os
import json
import time
import threading
import requests
from typing import Optional, Callable, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class DownloadStatus(Enum):
    QUEUED = "Queued"
    DOWNLOADING = "Downloading"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    ERROR = "Error"
    STOPPED = "Stopped"
    MERGING = "Merging"


@dataclass
class ChunkInfo:
    index: int
    start: int
    end: int
    downloaded: int = 0
    completed: bool = False


@dataclass
class DownloadState:
    url: str
    filepath: str
    total_size: int
    chunks: List[ChunkInfo]
    completed: bool = False
    timestamp: float = field(default_factory=time.time)


class ChunkDownloader(threading.Thread):
    """Downloads a single byte-range chunk of a file."""

    def __init__(self, url: str, chunk: ChunkInfo, temp_dir: str,
                 headers: dict, proxy: Optional[str] = None,
                 on_progress: Optional[Callable] = None,
                 cancel_event: Optional[threading.Event] = None,
                 pause_event: Optional[threading.Event] = None):
        super().__init__(daemon=True)
        self.url = url
        self.chunk = chunk
        self.temp_dir = temp_dir
        self.headers = dict(headers)
        self.proxy = proxy
        self.on_progress = on_progress
        self.cancel_event = cancel_event or threading.Event()
        self.pause_event = pause_event or threading.Event()
        self.error: Optional[Exception] = None
        self.chunk_file = os.path.join(temp_dir, f"chunk_{chunk.index:04d}.tmp")

    def run(self):
        start = self.chunk.start + self.chunk.downloaded
        end = self.chunk.end

        if start > end:
            self.chunk.completed = True
            return

        # Resume partial chunk from existing file
        mode = 'ab' if self.chunk.downloaded > 0 else 'wb'
        range_header = f"bytes={start}-{end}"
        req_headers = {**self.headers, 'Range': range_header}

        max_retries = 5
        for attempt in range(max_retries):
            try:
                proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else None
                with requests.get(self.url, headers=req_headers, stream=True,
                                  timeout=30, proxies=proxies, verify=False) as resp:
                    if resp.status_code not in (200, 206):
                        raise Exception(f"HTTP {resp.status_code}")

                    with open(self.chunk_file, mode) as f:
                        for data in resp.iter_content(chunk_size=65536):
                            if self.cancel_event.is_set():
                                return
                            # Handle pause
                            while self.pause_event.is_set():
                                if self.cancel_event.is_set():
                                    return
                                time.sleep(0.2)
                            if data:
                                f.write(data)
                                n = len(data)
                                self.chunk.downloaded += n
                                if self.on_progress:
                                    self.on_progress(n)

                self.chunk.completed = True
                return

            except Exception as e:
                self.error = e
                logger.error(f"Chunk {self.chunk.index} attempt {attempt+1} failed: {e}")
                import traceback
                with open('idm_debug.txt', 'a') as df:
                    df.write(f"Chunk {self.chunk.index} error: {e}\n")
                    traceback.print_exc(file=df)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
                mode = 'ab'


class MultiThreadedDownloader:
    """
    Downloads a file using multiple parallel threads (chunks).
    Supports pause, resume, and cancellation.
    """

    # Supported range of connections
    MIN_CONNECTIONS = 1
    MAX_CONNECTIONS = 32

    def __init__(self, task_id: str, url: str, filepath: str,
                 connections: int = 8, headers: Optional[dict] = None,
                 proxy: Optional[str] = None,
                 on_progress: Optional[Callable] = None,
                 on_status_change: Optional[Callable] = None,
                 speed_limit_bytes: int = 0):
        self.task_id = task_id
        self.url = url
        self.filepath = filepath
        self.connections = max(self.MIN_CONNECTIONS, min(self.MAX_CONNECTIONS, connections))
        self.headers = headers or {}
        self.proxy = proxy
        self.on_progress = on_progress          # fn(bytes_done, total, speed, eta)
        self.on_status_change = on_status_change # fn(status: DownloadStatus)
        self.speed_limit_bytes = speed_limit_bytes

        self.status = DownloadStatus.QUEUED
        self.total_size = 0
        self.downloaded_bytes = 0
        self.speed = 0.0  # bytes/sec
        self.eta = 0      # seconds

        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.RLock()
        self._speed_samples: List[tuple] = []  # (timestamp, bytes)

        # Temp directory for this download
        self.temp_dir = filepath + ".parts"
        self.state_file = filepath + ".partinfo"

    def _state_path(self):
        return self.state_file

    def _save_state(self, chunks: List[ChunkInfo]):
        state = DownloadState(
            url=self.url,
            filepath=self.filepath,
            total_size=self.total_size,
            chunks=chunks
        )
        with open(self._state_path(), 'w') as f:
            json.dump({
                'url': state.url,
                'filepath': state.filepath,
                'total_size': state.total_size,
                'chunks': [asdict(c) for c in state.chunks],
                'completed': state.completed
            }, f)

    def _load_state(self) -> Optional[DownloadState]:
        if not os.path.exists(self._state_path()):
            return None
        try:
            with open(self._state_path(), 'r') as f:
                data = json.load(f)
            chunks = [ChunkInfo(**c) for c in data['chunks']]
            return DownloadState(
                url=data['url'],
                filepath=data['filepath'],
                total_size=data['total_size'],
                chunks=chunks,
                completed=data.get('completed', False)
            )
        except Exception:
            return None

    def _get_file_info(self):
        """Probe URL for file size and range support."""
        headers = {**self.headers, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WITTGrp/1.0'}
        try:
            resp = requests.head(self.url, headers=headers, timeout=15,
                                 allow_redirects=True, verify=False)
            # Follow redirect for real URL
            self.url = resp.url
            size = int(resp.headers.get('Content-Length', 0))
            accepts_ranges = resp.headers.get('Accept-Ranges', '').lower() == 'bytes'
            return size, accepts_ranges
        except Exception:
            return 0, False

    def _chunk_progress(self, n_bytes: int):
        with self._lock:
            self.downloaded_bytes += n_bytes
            now = time.time()
            
            # Aggregate bytes locally to prevent O(N^2) scaling of list operations
            self._bytes_since_last_sample = getattr(self, '_bytes_since_last_sample', 0) + n_bytes

            # Update speeds and UI no more than 5 times per second
            if now - getattr(self, '_last_notify', 0.0) >= 0.2:
                self._speed_samples.append((now, self._bytes_since_last_sample))
                self._bytes_since_last_sample = 0
                
                # Keep only last 3 seconds of samples
                cutoff = now - 3.0
                self._speed_samples = [(t, b) for t, b in self._speed_samples if t >= cutoff]
                
                total_bytes_in_window = sum(b for _, b in self._speed_samples)
                time_window = now - self._speed_samples[0][0] if len(self._speed_samples) > 1 else 1.0
                self.speed = total_bytes_in_window / max(time_window, 0.01)
                
                self._last_notify = now
                should_notify = True
            else:
                should_notify = False

            remaining = max(self.total_size - self.downloaded_bytes, 0)
            self.eta = int(remaining / self.speed) if self.speed > 0 else 0

        if should_notify and self.on_progress:
            self.on_progress(self.downloaded_bytes, self.total_size, self.speed, self.eta)

    def _set_status(self, status: DownloadStatus):
        self.status = status
        if self.on_status_change:
            self.on_status_change(status)

    def start_download(self):
        """Start or resume the download in the current thread."""
        os.makedirs(self.temp_dir, exist_ok=True)
        self._set_status(DownloadStatus.DOWNLOADING)

        # Check for existing state (resume)
        state = self._load_state()
        if state and state.url == self.url and not state.completed:
            self.total_size = state.total_size
            chunks = state.chunks
            self.downloaded_bytes = sum(c.downloaded for c in chunks)
            logger.info(f"Resuming download: {self.filepath} ({self.downloaded_bytes}/{self.total_size})")
        else:
            # Fresh download
            size, accepts_ranges = self._get_file_info()
            self.total_size = size

            if size > 0 and accepts_ranges and self.connections > 1:
                chunks = self._split_into_chunks(size)
            else:
                # Single connection fallback
                chunks = [ChunkInfo(index=0, start=0, end=max(size - 1, 0))]
            self._save_state(chunks)

        # Download all incomplete chunks
        success = self._run_chunks(chunks)

        if success and not self._cancel_event.is_set():
            self._set_status(DownloadStatus.MERGING)
            self._merge_chunks(chunks)
            self._cleanup(chunks)
            self._set_status(DownloadStatus.COMPLETED)
        elif self._cancel_event.is_set():
            self._set_status(DownloadStatus.STOPPED)
        else:
            self._set_status(DownloadStatus.ERROR)

    def _split_into_chunks(self, size: int) -> List[ChunkInfo]:
        chunk_size = size // self.connections
        chunks = []
        for i in range(self.connections):
            start = i * chunk_size
            end = start + chunk_size - 1 if i < self.connections - 1 else size - 1
            chunks.append(ChunkInfo(index=i, start=start, end=end))
        return chunks

    def _run_chunks(self, chunks: List[ChunkInfo]) -> bool:
        threads = []
        for chunk in chunks:
            if chunk.completed:
                continue
            t = ChunkDownloader(
                url=self.url,
                chunk=chunk,
                temp_dir=self.temp_dir,
                headers={**self.headers, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WITTGrp/1.0'},
                proxy=self.proxy,
                on_progress=self._chunk_progress,
                cancel_event=self._cancel_event,
                pause_event=self._pause_event,
            )
            threads.append(t)
            t.start()

        if not threads:
            return all(c.completed for c in chunks)

        # Monitor and save state periodically
        state_save_interval = 3.0
        last_save = time.time()
        while any(t.is_alive() for t in threads):
            if self._cancel_event.is_set():
                 break
            time.sleep(0.5)
            now = time.time()
            if now - last_save > state_save_interval:
                self._save_state(chunks)
                last_save = now

        self._save_state(chunks)
        return all(c.completed for c in chunks) and not any(
            t.error for t in threads if not t.chunk.completed
        )

    def _merge_chunks(self, chunks: List[ChunkInfo]):
        """Merge all chunk temp files into the final file."""
        os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
        with open(self.filepath, 'wb') as out:
            for chunk in sorted(chunks, key=lambda c: c.index):
                chunk_file = os.path.join(self.temp_dir, f"chunk_{chunk.index:04d}.tmp")
                if os.path.exists(chunk_file):
                    with open(chunk_file, 'rb') as f:
                        while True:
                            buf = f.read(1024 * 1024)
                            if not buf:
                                break
                            out.write(buf)

    def _cleanup(self, chunks: List[ChunkInfo]):
        for chunk in chunks:
            chunk_file = os.path.join(self.temp_dir, f"chunk_{chunk.index:04d}.tmp")
            if os.path.exists(chunk_file):
                os.remove(chunk_file)
        try:
            os.rmdir(self.temp_dir)
        except Exception:
            pass
        if os.path.exists(self.state_file):
            os.remove(self.state_file)

    def pause(self):
        self._pause_event.set()
        self._set_status(DownloadStatus.PAUSED)

    def resume(self):
        self._pause_event.clear()
        if self.status == DownloadStatus.PAUSED:
            self._set_status(DownloadStatus.DOWNLOADING)

    def cancel(self):
        self._cancel_event.set()
        self._pause_event.clear()

    def stop_and_save(self):
        """Stop download but keep partial state for later resume."""
        self._cancel_event.set()
        self._pause_event.clear()
