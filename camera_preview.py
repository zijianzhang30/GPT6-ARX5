#!/usr/bin/env python3
"""Local Gemini RGB preview. Selects Orbbec MJPEG-capable V4L2 interface only."""
import fcntl,glob,json,os,struct,subprocess,threading,time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path

def find_gemini():
    for path in glob.glob('/dev/video*'):
        fd=None
        try:
            fd=os.open(path,os.O_RDWR|os.O_NONBLOCK)
            info=bytearray(104);fcntl.ioctl(fd,0x80685600,info)
            name=bytes(info[16:48]).split(b'\0')[0].decode()
            if 'Orbbec' not in name:continue
            for i in range(20):
                fmt=bytearray(64);struct.pack_into('II',fmt,0,i,1)
                try:fcntl.ioctl(fd,0xc0405602,fmt)
                except OSError:break
                if fmt[44:48]==b'MJPG':return path
        except OSError:pass
        finally:
            if fd is not None:os.close(fd)
    raise RuntimeError('未找到 Gemini 彩色接口，请检查 USB 连接。不会切换到笔记本摄像头。')

class Camera:
    def __init__(self):
        self.lock=threading.Lock();self.frame=None;self.at=0.;self.seq=0;self.error='';self.device=''
        self.proc=None;self.used=0.;self.closed=False
        threading.Thread(target=self.run,daemon=True).start()
    def run(self):
        while not self.closed:
            if time.monotonic()-self.used>4:
                time.sleep(.1);continue
            try:
                self.device=find_gemini();self.error=''
                proc=subprocess.Popen(['gst-launch-1.0','-q','v4l2src','device='+self.device,'!','video/x-raw,format=YUY2,width=848,height=480,framerate=30/1','!','videoconvert','!','jpegenc','quality=85','!','fdsink','fd=1'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
                self.proc=proc
                def watchdog():
                    while proc.poll() is None:
                        if self.closed or time.monotonic()-self.used>4:proc.terminate();return
                        time.sleep(.2)
                threading.Thread(target=watchdog,daemon=True).start()
                buf=b''
                while not self.closed:
                    chunk=os.read(proc.stdout.fileno(),65536)
                    if not chunk:break
                    buf+=chunk
                    while True:
                        a=buf.find(b'\xff\xd8');b=buf.find(b'\xff\xd9',a+2) if a>=0 else -1
                        if b<0:break
                        with self.lock:self.frame=buf[a:b+2];self.at=time.monotonic();self.seq+=1
                        buf=buf[b+2:]
                    if len(buf)>4000000:raise RuntimeError('摄像头帧格式异常')
                if time.monotonic()-self.used<4 and not self.closed:self.error='Gemini 取流中断，正在重试；请检查设备是否被占用。'
            except Exception as e:self.error=str(e)
            finally:
                if self.proc:
                    if self.proc.poll() is None:self.proc.terminate()
                    try:self.proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:self.proc.kill();self.proc.wait()
                    self.proc.stdout.close();self.proc=None
                with self.lock:self.frame=None
            time.sleep(.3)
    def get(self):
        self.used=time.monotonic();end=self.used+3
        while time.monotonic()<end:
            with self.lock:
                if self.frame and time.monotonic()-self.at<1:return self.frame,self.seq
            time.sleep(.02)
        raise RuntimeError(self.error or '等待 Gemini 画面超时，请检查 USB 连接。')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_GET(self):
        path=self.path.split('?')[0]
        try:
            if path=='/':body=Path(__file__).with_name('web').joinpath('camera.html').read_bytes();kind='text/html; charset=utf-8';seq=None
            elif path=='/frame.jpg':body,seq=self.server.camera.get();kind='image/jpeg'
            else:self.send_error(404);return
            self.send_response(200);self.send_header('Content-Type',kind);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            if seq is not None:self.send_header('X-Frame-Id',str(seq))
            self.end_headers();self.wfile.write(body)
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            body=json.dumps({'error':str(e)},ensure_ascii=False).encode()
            self.send_response(503);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers()
            try:self.wfile.write(body)
            except OSError:pass

if __name__=='__main__':
    server=ThreadingHTTPServer(('127.0.0.1',8767),Handler);server.daemon_threads=True;server.camera=Camera()
    print('Gemini 实时画面：http://127.0.0.1:8767 （仅 Gemini，不控制机械臂）',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.camera.closed=True;server.server_close()
