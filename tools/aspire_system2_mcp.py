#!/usr/bin/env python3
"""Serve a local stdio MCP session for the attended ARX R5 host."""
import argparse
import base64
import json
from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aspire_review import CAMERAS, HOST_TIMEOUT_S, MAX_REQUEST_BYTES, MOTION_TOOLS, failure

PROTOCOL_VERSIONS = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
TASK_INSTRUCTION = ('Use the physical left arm to sweep three blocks into the fixed dustpan. '
                    'Read the L3-04 ASPIRE transfer guide. Use the live RGB views and the left-arm base. '
                    'Verify the final result visually with the brush withdrawn.')
TOOL_DESCRIPTIONS = {
    'r5_task': 'Read the L3-04 task and physical arm roles.',
    'get_capability_graph': 'Read available tools and station capabilities.',
    'observe': 'Read fresh RGB views, measured TCP poses and gripper telemetry.',
    'cap_move_to_pose': 'Request one reviewed left TCP pose in left_base, metres and WXYZ.',
    'cap_set_gripper': 'Request one bounded normalized left gripper opening. Use the reported next-opening bounds.',
}


def schema(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required),
            'additionalProperties': False}


def vector_schema(length):
    return {'type': 'array', 'items': {'type': 'number'}, 'minItems': length, 'maxItems': length}


def list_tools(allow_motion):
    text = {'type': 'string', 'minLength': 1}
    shared = {'arm': {'const': 'left'}, 'note': text, 'observation_id': text}
    inputs = {
        'observe': schema({'cameras': {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                       'items': {'type': 'string', 'enum': list(CAMERAS)}}}),
        'r5_task': schema({}),
        'get_capability_graph': schema({}),
        'cap_move_to_pose': schema({**shared, 'target_pose': schema({
            'position': vector_schema(3), 'quaternion_wxyz': vector_schema(4),
            'frame': {'const': 'left_base'}}, ('position', 'quaternion_wxyz', 'frame'))},
            ('note', 'observation_id', 'target_pose')),
        'cap_set_gripper': schema({**shared, 'position': {'type': 'number', 'minimum': 0, 'maximum': 1}},
                                  ('note', 'observation_id', 'position')),
    }
    return [{'name': name, 'description': TOOL_DESCRIPTIONS[name], 'inputSchema': contract}
            for name, contract in inputs.items() if allow_motion or name not in MOTION_TOOLS]


def host_call(path, tool, args):
    request = json.dumps({'tool': tool, 'arguments': args}, allow_nan=False).encode() + b'\n'
    if len(request) > MAX_REQUEST_BYTES:
        raise ValueError('Request exceeds the review socket limit')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
        conn.settimeout(HOST_TIMEOUT_S + 5)
        try:
            conn.connect(str(path))
        except OSError as exc:
            return failure('not_dispatched', f'Review socket unavailable: {exc}')
        try:
            conn.sendall(request)
            with conn.makefile('rb') as stream:
                return json.loads(stream.readline(1024 * 1024))
        except (OSError, ValueError):
            return failure('outcome_unknown', 'Review response unavailable. Inspect host state before issuing another action.')


def tool_result(data, cameras):
    observation = data.get('observation')
    frames = []
    if observation:
        paths = observation.pop('images')
        for name in cameras:
            try:
                jpeg = Path(paths[name]).read_bytes()
                if not jpeg.startswith(b'\xff\xd8'):
                    raise ValueError('not a JPEG')
            except (KeyError, OSError, ValueError):
                data['observation'] = None
                data['observation_error'] = f'Unable to read fresh {name}; request another observation.'
                frames = []
                break
            frames.extend([{'type': 'text', 'text': 'camera: ' + name},
                           {'type': 'image', 'mimeType': 'image/jpeg',
                            'data': base64.b64encode(jpeg).decode('ascii')}])
    data['image_cameras'] = [f['text'][8:] for f in frames if f['type'] == 'text']
    content = [{'type': 'text', 'text': json.dumps(data, ensure_ascii=False)}, *frames]
    return {'content': content, 'structuredContent': data,
            'isError': not data.get('ok') or 'observation_error' in data}


def call_tool(path, name, arguments, allow_motion):
    if name in ('r5_task', 'get_capability_graph'):
        if arguments:
            raise ValueError(f'{name} takes no arguments')
        if name == 'r5_task':
            return tool_result({'ok': True, 'task': 'L3-04', 'station': 'physical_arx_r5',
                                'instruction': TASK_INSTRUCTION, 'manipulation_arms': ['left']}, ())
        return tool_result({'ok': True, 'station': 'physical_arx_r5', 'camera_mode': 'rgb',
                            'motion_tools_exposed': allow_motion, 'motion_frame': 'left_base',
                            'depth_backprojection': False, 'collision_checked': False,
                            'tools': list_tools(allow_motion), 'programs': [],
                            'configured_providers': {'ik': ['arx_r5'], 'segmentation': [], 'pose_planning': ['arx_r5']}}, ())
    if name == 'observe':
        cameras = arguments.get('cameras', list(CAMERAS))
        if (set(arguments) - {'cameras'} or not isinstance(cameras, list) or not cameras
                or any(not isinstance(v, str) or v not in CAMERAS for v in cameras)
                or len(cameras) != len(set(cameras))):
            raise ValueError('Select a nonempty list of distinct camera names')
        return tool_result(host_call(path, name, {}), cameras)
    if name not in MOTION_TOOLS or not allow_motion:
        raise ValueError('Tool is not available in this session')
    return tool_result(host_call(path, name, arguments), list(CAMERAS))


def rpc(message, path, allow_motion):
    method = message.get('method')
    if 'id' not in message and isinstance(method, str) and method.startswith('notifications/'):
        return None
    reply = {'jsonrpc': '2.0', 'id': message.get('id')}
    params = message.get('params', {})
    if message.get('jsonrpc') != '2.0' or not isinstance(params, dict):
        return {**reply, 'error': {'code': -32600, 'message': 'Invalid request'}}
    if method == 'initialize':
        version = params.get('protocolVersion')
        result = {'protocolVersion': version if version in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[0],
                  'capabilities': {'tools': {}}, 'serverInfo': {'name': 'arx-r5-aspire-system2', 'version': '0.1.0'}}
    elif method == 'ping':
        result = {}
    elif method == 'tools/list':
        result = {'tools': list_tools(allow_motion)}
    elif method == 'tools/call':
        name, arguments = params.get('name'), params.get('arguments', {})
        try:
            if not isinstance(arguments, dict):
                raise ValueError('Tool arguments must be an object')
            result = call_tool(path, name, arguments, allow_motion)
        except ValueError as exc:
            result = tool_result(failure('rejected', str(exc)), ())
    else:
        return {**reply, 'error': {'code': -32601, 'message': 'Method not found'}}
    return {**reply, 'result': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', type=Path, required=True)
    parser.add_argument('--allow-motion', action='store_true', help='Expose motion tools when the host also enables them')
    args = parser.parse_args()
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('Expected a JSON-RPC object')
        except ValueError:
            response = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Invalid JSON-RPC message'}}
        else:
            response = rpc(message, args.socket.expanduser().absolute(), args.allow_motion)
        if response is not None:
            print(json.dumps(response, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
