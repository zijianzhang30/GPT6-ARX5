#!/usr/bin/env python3
"""Read Orbbec 2.9.3 RGB profile calibration without starting camera streams.

Uses the official SDK C ABI, independent of the Python wheel's CPython version.
Writes an evidence report only; never installs values into robot calibration.
"""
import argparse
import ctypes as c
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


class Intrinsic(c.Structure):
    _fields_ = [(n, c.c_float) for n in ('fx', 'fy', 'cx', 'cy')] + [
        ('width', c.c_int16), ('height', c.c_int16)]


class Distortion(c.Structure):
    _fields_ = [(n, c.c_float) for n in ('k1', 'k2', 'k3', 'k4', 'k5', 'k6', 'p1', 'p2')] + [
        ('model', c.c_int)]


class SDK:
    def __init__(self, library):
        self.lib = c.CDLL(str(library.resolve()))
        self.bind('ob_get_version', c.c_int, [])
        self.bind('ob_error_get_message', c.c_char_p, [c.c_void_p])
        self.bind('ob_delete_error', None, [c.c_void_p])
        if self.lib.ob_get_version() != 20903:
            raise ValueError('Only the inspected Orbbec SDK 2.9.3 ABI is supported')
        error = c.POINTER(c.c_void_p)
        signatures = {
            'ob_set_logger_severity': (None, [c.c_int]),
            'ob_create_context_with_config': (c.c_void_p, [c.c_char_p]),
            'ob_query_device_list': (c.c_void_p, [c.c_void_p]),
            'ob_device_list_get_count': (c.c_uint32, [c.c_void_p]),
            'ob_device_list_get_device_serial_number': (c.c_char_p, [c.c_void_p, c.c_uint32]),
            'ob_device_list_get_device_by_serial_number': (c.c_void_p, [c.c_void_p, c.c_char_p]),
            'ob_device_get_sensor': (c.c_void_p, [c.c_void_p, c.c_int]),
            'ob_sensor_get_stream_profile_list': (c.c_void_p, [c.c_void_p]),
            'ob_stream_profile_list_get_count': (c.c_uint32, [c.c_void_p]),
            'ob_stream_profile_list_get_profile': (c.c_void_p, [c.c_void_p, c.c_int]),
            'ob_stream_profile_get_format': (c.c_int, [c.c_void_p]),
            'ob_video_stream_profile_get_width': (c.c_uint32, [c.c_void_p]),
            'ob_video_stream_profile_get_height': (c.c_uint32, [c.c_void_p]),
            'ob_video_stream_profile_get_fps': (c.c_uint32, [c.c_void_p]),
            'ob_video_stream_profile_get_intrinsic': (Intrinsic, [c.c_void_p]),
            'ob_video_stream_profile_get_distortion': (Distortion, [c.c_void_p]),
        }
        for name in ('context', 'device_list', 'device', 'sensor', 'stream_profile_list', 'stream_profile'):
            signatures['ob_delete_'+name] = (None, [c.c_void_p])
        for name, (returns, args) in signatures.items():
            self.bind(name, returns, [*args, error])

    def bind(self, name, returns, args):
        function = getattr(self.lib, name)
        function.restype, function.argtypes = returns, args

    def call(self, name, *args):
        error = c.c_void_p()
        result = getattr(self.lib, name)(*args, c.byref(error))
        if error:
            try:
                message = self.lib.ob_error_get_message(error).decode(errors='replace')
            finally:
                self.lib.ob_delete_error(error)
            raise RuntimeError(name+': '+message)
        return result

    def own(self, stack, kind, name, *args):
        handle = self.call(name, *args)
        if not handle:
            raise RuntimeError('Null SDK handle from '+name)
        stack.callback(self.call, 'ob_delete_'+kind, handle)
        return handle


def fields(structure):
    return {name: getattr(structure, name) for name, _ in structure._fields_}


def read_factory(library, config, serial, width, height, fps):
    root = ET.parse(config).getroot()
    if (root.findtext('Device/LinuxUVCBackend') != 'V4L2'
            or root.findtext('Device/Gemini305/LinuxUVCAutoRebootOnFault') != 'false'
            or root.findtext('Device/EnumerateNetDevice') != 'false'):
        raise ValueError('Use V4L2 config with Gemini305 auto reboot and network enumeration disabled')
    sdk = SDK(library)
    sdk.call('ob_set_logger_severity', 3)
    with ExitStack() as stack:
        context = sdk.own(stack, 'context', 'ob_create_context_with_config', str(config.resolve()).encode())
        devices = sdk.own(stack, 'device_list', 'ob_query_device_list', context)
        serials = [sdk.call('ob_device_list_get_device_serial_number', devices, i).decode()
                   for i in range(sdk.call('ob_device_list_get_count', devices))]
        if serial not in serials:
            return {'sdk_version': '2.9.3', 'status': 'device_not_enumerated',
                    'requested_serial': serial, 'enumerated_serials': serials,
                    'stream_started': False, 'robot_accessed': False,
                    'matching_rgb_profiles': [], 'applied_to_robot_profile': False}
        device = sdk.own(stack, 'device', 'ob_device_list_get_device_by_serial_number', devices, serial.encode())
        sensor = sdk.own(stack, 'sensor', 'ob_device_get_sensor', device, 2)
        profiles = sdk.own(stack, 'stream_profile_list', 'ob_sensor_get_stream_profile_list', sensor)
        available, matches = [], []
        for index in range(sdk.call('ob_stream_profile_list_get_count', profiles)):
            with ExitStack() as profile_stack:
                p = sdk.own(profile_stack, 'stream_profile', 'ob_stream_profile_list_get_profile', profiles, index)
                metadata = {k: sdk.call('ob_video_stream_profile_get_'+k, p) for k in ('width', 'height', 'fps')}
                metadata['format'] = sdk.call('ob_stream_profile_get_format', p)
                available.append(metadata)
                if metadata != {'width': width, 'height': height, 'fps': fps, 'format': 5}:
                    continue
                matches.append({**metadata, 'intrinsic': fields(sdk.call('ob_video_stream_profile_get_intrinsic', p)),
                                'distortion': fields(sdk.call('ob_video_stream_profile_get_distortion', p))})
    return {'sdk_version': '2.9.3', 'library_sha256': hashlib.sha256(library.read_bytes()).hexdigest(),
            'serial': serial, 'stream_started': False, 'robot_accessed': False,
            'available_profiles': available, 'matching_rgb_profiles': matches,
            'uvc_image_geometry_verified': False, 'applied_to_robot_profile': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', required=True, type=Path)
    parser.add_argument('--config', required=True, type=Path,
                        help='SDK config with V4L2 backend and automatic reboot disabled')
    parser.add_argument('--serial', required=True)
    parser.add_argument('--width', type=int, default=848)
    parser.add_argument('--height', type=int, default=480)
    parser.add_argument('--fps', type=int, default=30)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists; use a new evidence filename')
    report = read_factory(args.library, args.config, args.serial, args.width, args.height, args.fps)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({'output': str(args.output), 'matches': report['matching_rgb_profiles']}))
    return 0 if report['matching_rgb_profiles'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
