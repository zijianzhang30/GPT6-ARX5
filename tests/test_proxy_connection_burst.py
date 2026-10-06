"""Exercise actual TCP admission without importing or commanding robot hardware."""
import socket
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from tempfile import TemporaryDirectory
from unittest.mock import patch
from pathlib import Path

from record_workbench import RecordingWorkbench


class ProxyConnectionBurstTests(unittest.TestCase):
    def test_camera_and_watchdog_burst_survives_brief_accept_delay(self):
        with TemporaryDirectory() as directory, \
                patch('record_workbench.Upstream'), \
                patch('record_workbench.Demonstrations') as recorder:
            recorder.return_value.status.return_value = {'episode': None}
            server = RecordingWorkbench(('127.0.0.1', 0),
                                        'http://127.0.0.1:1', Path(directory))
            gate = threading.Barrier(13)

            def get(_):
                gate.wait(timeout=2)
                # The production HTTP timeout remains 0.25 seconds.
                with socket.create_connection(server.server_address, timeout=.25) as client:
                    client.sendall(b'GET /api/recording/status HTTP/1.0\r\n'
                                   b'Host: localhost\r\n\r\n')
                    response = bytearray()
                    while block := client.recv(4096):
                        response.extend(block)
                    return bytes(response)

            worker = None
            try:
                with ThreadPoolExecutor(max_workers=12) as pool:
                    futures = [pool.submit(get, i) for i in range(12)]
                    gate.wait(timeout=2)
                    # Connections arrive during a short scheduler pause.
                    time.sleep(.05)
                    worker = threading.Thread(target=server.serve_forever,
                                              kwargs={'poll_interval': .01}, daemon=True)
                    worker.start()
                    for future in futures:
                        self.assertIn(b'200 OK', future.result(timeout=2))
            finally:
                if worker:
                    server.shutdown()
                    worker.join(timeout=2)
                server.server_close()


if __name__ == '__main__':
    unittest.main()
