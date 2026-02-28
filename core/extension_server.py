"""
Extension Server - Receives download requests from browser extension
Listens on localhost:9614 (HTTP)
"""
import json
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ExtensionHandler(BaseHTTPRequestHandler):
    queue_manager = None
    add_dialog_callback: Optional[Callable] = None

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors()
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        self.send_response(200)
        self._send_cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        try:
            data = json.loads(body)
            path = self.path.rstrip('/')

            if path == '/add':
                self._handle_add(data)
                self.wfile.write(json.dumps({'status': 'ok'}).encode())
            elif path == '/ping':
                self.wfile.write(json.dumps({'status': 'running', 'version': '1.0'}).encode())
            else:
                self.wfile.write(json.dumps({'status': 'unknown_path'}).encode())
        except Exception as e:
            logger.error(f"Extension server error: {e}")
            self.wfile.write(json.dumps({'status': 'error', 'msg': str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self._send_cors()
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'running', 'version': '1.0'}).encode())

    def _handle_add(self, data: dict):
        url = data.get('url', '')
        if not url:
            return
        referer = data.get('referer', '')
        filename = data.get('filename', '')
        extra_headers = data.get('headers', {})

        if self.add_dialog_callback:
            # Show add-download dialog in the UI thread
            self.add_dialog_callback(url, filename, referer, extra_headers)
        elif self.queue_manager:
            self.queue_manager.add_download(
                url=url,
                filename=filename or None,
                referer=referer,
                extra_headers=extra_headers,
                auto_start=True,
            )

    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def log_message(self, format, *args):
        pass  # Suppress default access log


class ExtensionServer:
    def __init__(self, port: int = 9614,
                 queue_manager=None,
                 add_dialog_callback: Optional[Callable] = None):
        self.port = port
        ExtensionHandler.queue_manager = queue_manager
        ExtensionHandler.add_dialog_callback = add_dialog_callback
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        try:
            self._server = HTTPServer(('127.0.0.1', self.port), ExtensionHandler)
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            logger.info(f"Extension server started on port {self.port}")
        except Exception as e:
            logger.error(f"Failed to start extension server: {e}")

    def stop(self):
        if self._server:
            self._server.shutdown()

    def update_callbacks(self, queue_manager=None, add_dialog_callback=None):
        if queue_manager:
            ExtensionHandler.queue_manager = queue_manager
        if add_dialog_callback:
            ExtensionHandler.add_dialog_callback = add_dialog_callback
