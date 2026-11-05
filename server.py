"""Local dashboard server. API secrets and collector source are not web-served."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Timer
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent

class DashboardHandler(SimpleHTTPRequestHandler):
    def allowed_path(self):
        path = unquote(urlsplit(self.path).path)
        parts = Path(path).parts
        allowed = path in ('/', '/index.html', '/favicon.ico') or path.startswith(('/assets/', '/data/'))
        if not allowed or '..' in parts or any(part.startswith('.') for part in parts):
            return False
        return True

    def do_GET(self):
        if not self.allowed_path():
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        if not self.allowed_path():
            self.send_error(404)
            return
        super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404)
        return None

if __name__ == '__main__':
    handler = partial(DashboardHandler, directory=str(ROOT))
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        url = f'http://127.0.0.1:{server.server_port}/'
        print(f'등기등기: {url}\n종료: Ctrl+C', flush=True)
        Timer(0.5, lambda: webbrowser.open(url)).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('\n서버를 종료합니다.')
