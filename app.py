#!/usr/bin/env python3
"""One-command local R5 workbench; simulation never loads the hardware SDK."""
import argparse
import json
import mimetypes
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from camera_streams import CameraHub
from control import Controller
ROOT = Path(__file__).resolve().parent
MAX_COMMAND_BYTES = 16384
MAX_TRAJECTORY_BYTES = 2 * 1024 * 1024

class Workbench(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, live=False, channel='can0', cameras=None, *, validate_hold=False, supervised_policy=False,
                 wrist_serial='CV2C8610015R'):
        if live:
            from live_control import LiveController
            self.controller = LiveController(channel, experimental_hold=validate_hold,
                                             supervised_policy=supervised_policy)
        else:
            self.controller = Controller()
        self.lock = threading.RLock()
        self.token = secrets.token_urlsafe(32)
        self.done = threading.Event()
        super().__init__(address, Handler)
        self.cameras = cameras if cameras is not None else CameraHub(wrist_serial=wrist_serial)
        self.worker = threading.Thread(target=self.loop, daemon=True)
        self.worker.start()
    def loop(self):
        while not self.done.wait(.02):
            with self.lock:
                try:
                    self.controller.tick()
                except Exception as e:
                    self.controller.stop(f'控制循环异常，已暂停：{e}')
    def server_close(self):
        self.done.set()
        self.cameras.close()
        if hasattr(self.controller, 'close'):
            self.controller.close()
        super().server_close()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def send(self, status, body, kind='application/json; charset=utf-8', headers=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; img-src 'self' data: blob:; frame-ancestors 'none'")
        for name, value in (headers or {}).items():
            self.send_header(name, str(value))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/state':
            with self.server.lock:
                return self.send(200, self.server.controller.snapshot())
        parts = path.split('/')
        if len(parts) == 5 and parts[1:3] == ['api', 'cameras'] and parts[4] == 'frame.jpg':
            try:
                frame, sequence, device = self.server.cameras.get(parts[3])
                return self.send(200, frame, 'image/jpeg', {
                    'X-Frame-Id': sequence,
                    'X-Camera-Device': device,
                })
            except KeyError:
                return self.send(404, {'error': '相机不存在'})
            except RuntimeError as e:
                return self.send(503, {'error': str(e)})
        files = {'/': 'index.html', '/app.js': 'app.js', '/dual.js': 'dual.js', '/style.css': 'style.css'}
        if path not in files:
            return self.send(404, {'error': '页面不存在'})
        file = ROOT/'web'/files[path]
        body = file.read_bytes().replace(b'__TOKEN__', self.server.token.encode())
        self.send(200, body, (mimetypes.guess_type(file)[0] or 'text/plain')+'; charset=utf-8')
    def do_POST(self):
        if urlsplit(self.path).path != '/api/command':
            return self.send(404, {'error': '接口不存在'})
        origin = self.headers.get('Origin')
        if origin and origin != f'http://{self.headers.get("Host")}':
            return self.send(403, {'error': '不允许跨站控制'})
        if not secrets.compare_digest(self.headers.get('X-Control-Token', ''), self.server.token):
            return self.send(403, {'error': '请刷新控制页面'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_TRAJECTORY_BYTES:
                raise ValueError('请求过大或为空')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('请求格式错误')
            if size > MAX_COMMAND_BYTES and data.get('action') != 'policy_trajectory':
                raise ValueError('请求过大或为空')
            with self.server.lock:
                self.server.controller.command(data)
                state = self.server.controller.snapshot()
            self.send(200, state)
        except (ValueError, TypeError, KeyError, OverflowError) as e:
            self.send(400, {'error': str(e)})

def main():
    parser = argparse.ArgumentParser(description='ARX R5 离线工作台：6 关节 + 夹爪')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--live', action='store_true', help='实机模式（默认）')
    parser.add_argument('--sim', action='store_true', help='仅在显式指定时模拟')
    parser.add_argument('--can', default='can0')
    parser.add_argument('--wrist-serial', default='CV2C8610015R')
    parser.add_argument('--validate-hold', action='store_true',
                        help='Allow supervised empty-arm pause/hold validation; autonomous policy stays disabled')
    parser.add_argument('--supervised-policy', action='store_true',
                        help='Allow an attended, supported policy trial after measured hold qualification')
    args = parser.parse_args()
    try:
        server = Workbench(('127.0.0.1', args.port), live=not args.sim, channel=args.can,
                           validate_hold=args.validate_hold, supervised_policy=args.supervised_policy,
                           wrist_serial=args.wrist_serial)
    except OSError as e:
        parser.error(f'端口 {args.port} 无法使用：{e}。尝试 --port 8766')
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'ARX R5 工作台已启动：{url}\n{'离线模拟' if args.sim else '实机模式（等待网页连接）'} · 6 关节 + 1 夹爪 · Ctrl+C 关闭', flush=True)
    if not args.no_browser:
        threading.Timer(.5, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\n工作台已关闭。')
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
