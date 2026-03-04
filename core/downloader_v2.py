"""
Core Download Engine V2 - IDM-Style Dynamic Segmentation Downloader
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
class DynamicChunk:
    index: int
    start: int
    end: int
    downloaded: int = 0
    completed: bool = False
    active: bool = False

@dataclass
class DownloadState:
    url: str
    filepath: str
    total_size: int
    chunks: List[DynamicChunk]
    completed: bool = False
    timestamp: float = field(default_factory=time.time)

class DynamicDownloader:
    """
    V2 Downloader implementing Intelligent Dynamic File Segmentation.
    - Fixed pool of worker threads.
    - Reuses HTTP connections via requests.Session.
    - Dynamically splits the largest active chunk when a worker becomes idle.
    """

    MIN_CONNECTIONS = 1
    MAX_CONNECTIONS = 32
    MIN_SPLIT_SIZE = 1024 * 1024  # 1MB minimum chunk size to split

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
        self.on_progress = on_progress          
        self.on_status_change = on_status_change 
        self.speed_limit_bytes = speed_limit_bytes

        self.status = DownloadStatus.QUEUED
        self.total_size = 0
        self.downloaded_bytes = 0
        self.speed = 0.0  
        self.eta = 0      

        self.chunks: List[DynamicChunk] = []
        self._next_chunk_idx = 0

        self._cancel_event = threading.Event()
        self._pause_event = threading.Event()
        self._lock = threading.RLock()
        
        # Diagnostics
        self.error: Optional[Exception] = None
        
        # Speed measurement
        self._speed_samples: List[tuple] = []
        self._bytes_since_last_sample = 0
        self._last_notify = 0.0

        self.temp_dir = filepath + ".dynamic.parts"
        self.state_file = filepath + ".dynamic.partinfo"

    def _state_path(self): return self.state_file

    def _save_state(self):
        with self._lock:
            state = DownloadState(
                url=self.url,
                filepath=self.filepath,
                total_size=self.total_size,
                chunks=self.chunks,
                completed=(self.status == DownloadStatus.COMPLETED)
            )
            data = {
                'url': state.url,
                'filepath': state.filepath,
                'total_size': state.total_size,
                'chunks': [asdict(c) for c in state.chunks],
                'completed': state.completed,
                'next_idx': self._next_chunk_idx
            }
        try:
            with open(self._state_path(), 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> bool:
        if not os.path.exists(self._state_path()):
            return False
        try:
            with open(self._state_path(), 'r') as f:
                data = json.load(f)
            if data['url'] != self.url: return False
            if data.get('completed', False): return False
            
            self.total_size = data['total_size']
            self._next_chunk_idx = data.get('next_idx', len(data['chunks']))
            self.chunks = []
            for cdata in data['chunks']:
                cdata['active'] = False # Reset active flags on load
                self.chunks.append(DynamicChunk(**cdata))
            
            self.downloaded_bytes = sum(c.downloaded for c in self.chunks)
            return True
        except Exception:
            return False

    def _get_file_info(self):
        headers = {**self.headers, 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) WITTGrp/2.0'}
        try:
            resp = requests.head(self.url, headers=headers, timeout=15,
                                 allow_redirects=True, verify=False)
            self.url = resp.url
            size = int(resp.headers.get('Content-Length', 0))
            accepts = resp.headers.get('Accept-Ranges', '').lower() == 'bytes'
            return size, accepts
        except Exception:
            return 0, False

    def _set_status(self, status: DownloadStatus):
        self.status = status
        if self.on_status_change:
            self.on_status_change(status)

    def _update_progress(self, n_bytes: int):
        with self._lock:
            self.downloaded_bytes += n_bytes
            self._bytes_since_last_sample += n_bytes
            now = time.time()

            if now - self._last_notify >= 0.2:
                self._speed_samples.append((now, self._bytes_since_last_sample))
                self._bytes_since_last_sample = 0
                
                cutoff = now - 3.0
                self._speed_samples = [(t, b) for t, b in self._speed_samples if t >= cutoff]
                
                total_in_window = sum(b for _, b in self._speed_samples)
                time_window = now - self._speed_samples[0][0] if len(self._speed_samples) > 1 else 1.0
                self.speed = total_in_window / max(time_window, 0.01)
                self._last_notify = now

                rem = max(self.total_size - self.downloaded_bytes, 0)
                self.eta = int(rem / self.speed) if self.speed > 0 else 0
                should_notify = True
            else:
                should_notify = False

        if should_notify and self.on_progress:
            self.on_progress(self.downloaded_bytes, self.total_size, self.speed, self.eta)

    def _get_chunk_to_download(self) -> Optional[DynamicChunk]:
        """
        Core of IDM Dynamic Segmentation:
        1. Find an incomplete, inactive chunk (from resume).
        2. If none, find the active chunk with the largest remaining bytes.
        3. If it's big enough, split it in half and return the new second half.
        """
        with self._lock:
            # 1. Any idle chunks?
            for c in self.chunks:
                if not c.completed and not c.active:
                    c.active = True
                    return c

            
            # 2. Split the largest active chunk
            largest_chunk = None
            max_remaining = 0
            
            for c in self.chunks:
                if not c.completed and c.active:
                    remaining = c.end - (c.start + c.downloaded)
                    if remaining > max_remaining:
                        max_remaining = remaining
                        largest_chunk = c
            
            if largest_chunk and max_remaining > self.MIN_SPLIT_SIZE:
                # Calculate midpoint (round down)
                curr_pos = largest_chunk.start + largest_chunk.downloaded
                midpoint = curr_pos + (max_remaining // 2)
                
                # Create the new chunk for the 2nd half
                new_chunk = DynamicChunk(
                    index=self._next_chunk_idx,
                    start=midpoint,
                    end=largest_chunk.end,
                    active=True
                )
                self._next_chunk_idx += 1
                
                # Shrink the original chunk so its worker stops early
                largest_chunk.end = midpoint - 1
                
                self.chunks.append(new_chunk)
                logger.info(f"Dynamically split chunk {largest_chunk.index}: new boundaries {largest_chunk.end+1}-{new_chunk.end} (Thread {new_chunk.index})")
                return new_chunk
                
        return None

    def _worker_thread(self, session: requests.Session):
        """Worker loop: grabs chunks, reuses connections, downloads data."""
        while not self._cancel_event.is_set() and not self._pause_event.is_set():
            chunk = self._get_chunk_to_download()
            if not chunk:
                # No chunks available to split. Worker can sleep or exit.
                time.sleep(0.5)
                # If all chunks are truly complete, exit worker.
                with self._lock:
                    if all(c.completed for c in self.chunks):
                        break
                continue
                
            chunk_file = os.path.join(self.temp_dir, f"chunk_{chunk.index:04d}.tmp")
            
            try:
                # Handle dynamic boundaries inside the loop
                while not chunk.completed and not self._cancel_event.is_set():
                    while self._pause_event.is_set() and not self._cancel_event.is_set():
                        time.sleep(0.2)
                        
                    with self._lock:
                        start = chunk.start + chunk.downloaded
                        end = chunk.end
                        
                    if start > end:
                        chunk.completed = True
                        break

                    mode = 'ab' if chunk.downloaded > 0 else 'wb'
                    req_headers = {**self.headers, 'Range': f"bytes={start}-{end}"}
                    
                    # session.get reuses the TCP connection!
                    proxies = {'http': self.proxy, 'https': self.proxy} if self.proxy else None
                    with session.get(self.url, headers=req_headers, stream=True, 
                                     timeout=30, proxies=proxies, verify=False) as resp:
                        
                        if resp.status_code not in (200, 206) and resp.status_code != 416:
                            raise Exception(f"HTTP {resp.status_code}")
                            
                        if resp.status_code == 416: # Range Not Satisfiable (already done)
                            chunk.completed = True
                            break

                        # Increase disk buffering to 2MB to reduce OS write syscalls
                        with open(chunk_file, mode, buffering=2 * 1024 * 1024) as f:
                            # Use a larger network chunk size to reduce loop overhead
                            for data in resp.iter_content(chunk_size=1024 * 1024):
                                if self._cancel_event.is_set() or self._pause_event.is_set():
                                    break
                                
                                if data:
                                    n = len(data)
                                    # Fast unlocked check against end boundary
                                    if chunk.start + chunk.downloaded + n > chunk.end + 1:
                                        # We might be overshooting. Need to lock to carefully truncate.
                                        with self._lock:
                                            curr_pos = chunk.start + chunk.downloaded
                                            if curr_pos + n > chunk.end + 1:
                                                allowed = (chunk.end + 1) - curr_pos
                                                if allowed > 0:
                                                    f.write(data[:allowed])
                                                    chunk.downloaded += allowed
                                                    self._update_progress(allowed)
                                                chunk.completed = True
                                                break
                                            else:
                                                # Boundary changed while waiting for lock
                                                f.write(data)
                                                chunk.downloaded += n
                                                self._update_progress(n)
                                    else:
                                        # Safe unlocked write and local counter update
                                        f.write(data)
                                        chunk.downloaded += n
                                        
                                        # Fast check if chunk natively completed
                                        if chunk.start + chunk.downloaded >= chunk.end + 1:
                                            chunk.completed = True
                                            self._update_progress(n)
                                            break
                                            
                                        # Update global progress without holding the lock
                                        # (_update_progress handles its own very brief lock)
                                        self._update_progress(n)


                                            
            except Exception as e:
                logger.error(f"Worker chunk {chunk.index} failed: {e}")
                self.error = e
                break # worker exits on error, retry logic can be added later
            finally:
                with self._lock:
                    chunk.active = False
                    if chunk.start + chunk.downloaded >= chunk.end:
                        chunk.completed = True

    def start_download(self):
        os.makedirs(self.temp_dir, exist_ok=True)
        self._set_status(DownloadStatus.DOWNLOADING)

        resumed = self._load_state()
        if resumed:
            logger.info(f"Resuming dynamic download: {self.downloaded_bytes}/{self.total_size}")
        else:
            size, accepts = self._get_file_info()
            self.total_size = size
            if size > 0 and accepts:
                # Start with a single chunk covering the whole file!
                # It will aggressively dynamically split as threads spin up.
                self.chunks = [DynamicChunk(index=0, start=0, end=max(size - 1, 0))]
                self._next_chunk_idx = 1
            else:
                self.chunks = [DynamicChunk(index=0, start=0, end=max(size - 1, 0))]
                self.connections = 1
                self._next_chunk_idx = 1
            self._save_state()

        # Spin up persistent workers
        workers = []
        for i in range(self.connections):
            session = requests.Session()
            t = threading.Thread(target=self._worker_thread, args=(session,), daemon=True)
            workers.append(t)
            t.start()

        # Monitor loop
        state_save_interval = 2.0
        last_save = time.time()
        while any(w.is_alive() for w in workers):
            if self._cancel_event.is_set():
                break
            time.sleep(0.5)
            if time.time() - last_save > state_save_interval:
                self._save_state()
                last_save = time.time()

        self._save_state()
        
        with self._lock:
            all_done = all(c.completed for c in self.chunks)

        if all_done and not self._cancel_event.is_set():
            self._set_status(DownloadStatus.MERGING)
            self._merge_chunks()
            self._cleanup()
            self._set_status(DownloadStatus.COMPLETED)
        elif self._cancel_event.is_set():
            if self.error:
                self._set_status(DownloadStatus.ERROR)
            else:
                self._set_status(DownloadStatus.STOPPED)
        else:
            self._set_status(DownloadStatus.ERROR)

    def _merge_chunks(self):
        os.makedirs(os.path.dirname(self.filepath) or '.', exist_ok=True)
        with open(self.filepath, 'wb') as out:
            # Sort chunks by start byte to stitch correctly
            for chunk in sorted(self.chunks, key=lambda c: c.start):
                cf = os.path.join(self.temp_dir, f"chunk_{chunk.index:04d}.tmp")
                if os.path.exists(cf):
                    with open(cf, 'rb') as f:
                        while True:
                            buf = f.read(1024 * 1024)
                            if not buf: break
                            out.write(buf)

    def _cleanup(self):
        for chunk in self.chunks:
            cf = os.path.join(self.temp_dir, f"chunk_{chunk.index:04d}.tmp")
            if os.path.exists(cf): os.remove(cf)
        try: os.rmdir(self.temp_dir)
        except: pass
        if os.path.exists(self.state_file): os.remove(self.state_file)

    def pause(self):
        self._pause_event.set()
        self._set_status(DownloadStatus.PAUSED)
        self._save_state()

    def resume(self):
        self._pause_event.clear()
        if self.status in (DownloadStatus.PAUSED, DownloadStatus.ERROR):
            # To resume properly, we need to spin up the start loop again.
            # Usually managed by queue_manager re-calling start_download
            self._set_status(DownloadStatus.QUEUED)

    def cancel(self):
        self._cancel_event.set()
        self._pause_event.clear()

    def stop_and_save(self):
        self._cancel_event.set()
        self._pause_event.clear()
        self._save_state()
