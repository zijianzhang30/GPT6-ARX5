import unittest
from unittest.mock import patch

from camera_streams import CAMERAS, find_device


class CameraSelectionTests(unittest.TestCase):
    def test_wrist_identity_survives_video_node_reordering(self):
        spec = CAMERAS[0]
        with patch('camera_streams.glob.glob', return_value=['/dev/video2', '/dev/video18']), \
             patch('camera_streams._device_info', return_value=('Orbbec Gemini 305', {b'MJPG'})), \
             patch('camera_streams._device_serial', side_effect=lambda p:
                   'CV2C86100180' if p == '/dev/video2' else 'CV2C8610015R'):
            self.assertEqual(find_device(spec), '/dev/video18')

    def test_missing_left_camera_cannot_fall_back_to_right_camera(self):
        with patch('camera_streams.glob.glob', return_value=['/dev/video2']), \
             patch('camera_streams._device_info', return_value=('Orbbec Gemini 305', {b'MJPG'})), \
             patch('camera_streams._device_serial', return_value='CV2C86100180'):
            with self.assertRaises(RuntimeError):
                find_device(CAMERAS[0])

    def test_depth_or_metadata_node_is_not_selected_for_matching_serial(self):
        with patch('camera_streams.glob.glob', return_value=['/dev/video2', '/dev/video18']), \
             patch('camera_streams._device_info', side_effect=[
                 ('Orbbec Gemini 305', {b'Z16 '}), ('Orbbec Gemini 305', {b'MJPG'})]), \
             patch('camera_streams._device_serial', return_value='CV2C8610015R'):
            self.assertEqual(find_device(CAMERAS[0]), '/dev/video18')
