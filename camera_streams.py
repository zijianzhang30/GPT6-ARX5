#!/usr/bin/env python3
"""Lazy, local-only MJPEG capture for the two external workbench cameras."""
from dataclasses import dataclass, replace
import fcntl
import glob
import os
from pathlib import Path
import struct
import subprocess
import threading
import time


@dataclass(frozen=True)
class CameraSpec:
    key: str
    label: str
    name_fragment: str
    width: int
    height: int
    fps: int = 30
    serial: str | None = None


CAMERAS = (
    CameraSpec('gemini', 'Gemini 305', 'Orbbec Gemini 305', 848, 480,
               fps=15, serial='CV2C8610015R'),
    CameraSpec('external', '外接 RGB', 'USB 2.0 Camera', 640, 480),
)


def _video_number(path):
    try:
        return int(path.removeprefix('/dev/video'))
    except ValueError:
        return 10_000


def _device_info(path):
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    try:
        info = bytearray(104)
        fcntl.ioctl(fd, 0x80685600, info)  # VIDIOC_QUERYCAP
        name = bytes(info[16:48]).split(b'\0')[0].decode(errors='replace')
        formats = set()
        for index in range(32):
            fmt = bytearray(64)
            struct.pack_into('II', fmt, 0, index, 1)
            try:
                fcntl.ioctl(fd, 0xC0405602, fmt)  # VIDIOC_ENUM_FMT
            except OSError:
                break
            formats.add(bytes(fmt[44:48]))
        return name, formats
    finally:
        os.close(fd)


def _device_serial(path):
    device = (Path('/sys/class/video4linux') / Path(path).name / 'device').resolve()
    for parent in (device, *device.parents):
        try:
            return (parent / 'serial').read_text().strip()
        except OSError:
            continue
    return None


def find_device(spec):
    for path in sorted(glob.glob('/dev/video*'), key=_video_number):
        try:
            name, formats = _device_info(path)
        except OSError:
            continue
        if spec.name_fragment in name and b'MJPG' in formats:
            # Video node numbers change on reconnect; never substitute the other arm.
            if spec.serial is not None and _device_serial(path) != spec.serial:
                continue
            return path
    raise RuntimeError(f'未找到 {spec.label} 彩色接口；请检查 USB 连接和设备占用。')


class CameraStream:
    def __init__(self, spec):
        self.spec = spec
        self.lock = threading.Lock()
        self.frame = None
        self.frame_at = 0.0
        self.sequence = 0
        self.error = ''
        self.device = ''
        self.used_at = 0.0
        self.process = None
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _set_error(self, message):
        with self.lock:
            self.error = message

    def _watch(self, process):
        while process.poll() is None:
            if self.closed.is_set() or time.monotonic() - self.used_at > 4:
                process.terminate()
                return
            self.closed.wait(.2)

    def _run(self):
        while not self.closed.is_set():
            if time.monotonic() - self.used_at > 4:
                self.closed.wait(.1)
                continue
            process = None
            try:
                self.device = find_device(self.spec)
                caps = (
                    f'image/jpeg,width={self.spec.width},height={self.spec.height},'
                    f'framerate={self.spec.fps}/1'
                )
                process = subprocess.Popen(
                    ['gst-launch-1.0', '-q', 'v4l2src', f'device={self.device}',
                     '!', caps, '!', 'jpegparse', '!', 'fdsink', 'fd=1'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                self.process = process
                self._set_error('')
                threading.Thread(target=self._watch, args=(process,), daemon=True).start()
                buffer = b''
                while not self.closed.is_set():
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        break
                    buffer += chunk
                    while True:
                        start = buffer.find(b'\xff\xd8')
                        end = buffer.find(b'\xff\xd9', start + 2) if start >= 0 else -1
                        if end < 0:
                            break
                        with self.lock:
                            self.frame = buffer[start:end + 2]
                            self.frame_at = time.monotonic()
                            self.sequence += 1
                        buffer = buffer[end + 2:]
                    if len(buffer) > 4_000_000:
                        raise RuntimeError('摄像头返回了异常的 MJPEG 数据。')
                if time.monotonic() - self.used_at < 4 and not self.closed.is_set():
                    self._set_error(f'{self.spec.label} 取流中断，正在重试；设备可能被其他程序占用。')
            except Exception as exc:
                self._set_error(str(exc))
            finally:
                if process is not None:
                    if process.poll() is None:
                        process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    if process.stdout:
                        process.stdout.close()
                self.process = None
                with self.lock:
                    self.frame = None
            self.closed.wait(.3)

    def get(self):
        self.used_at = time.monotonic()
        deadline = self.used_at + 6
        while time.monotonic() < deadline and not self.closed.is_set():
            with self.lock:
                if self.frame and time.monotonic() - self.frame_at < 1:
                    return self.frame, self.sequence, self.device
                error = self.error
            self.closed.wait(.02)
        raise RuntimeError(error or f'等待 {self.spec.label} 画面超时，请检查 USB 连接。')

    def close(self):
        self.closed.set()
        process = self.process
        if process is not None and process.poll() is None:
            process.terminate()
        self.thread.join(timeout=3)


class CameraHub:
    def __init__(self, wrist_serial='CV2C8610015R'):
        self.streams = {spec.key: CameraStream(
            replace(spec, serial=wrist_serial) if spec.key == 'gemini' else spec)
            for spec in CAMERAS}

    def get(self, key):
        if key not in self.streams:
            raise KeyError(key)
        return self.streams[key].get()

    def close(self):
        for stream in self.streams.values():
            stream.close()
