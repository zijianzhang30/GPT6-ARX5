import json
import threading
import unittest
import urllib.request
import urllib.error
from app import Workbench

class FakeCameras:
    def __init__(self):
        self.closed=False
    def get(self,key):
        if key not in {'gemini','external'}:
            raise KeyError(key)
        return b'\xff\xd8test-frame\xff\xd9',7,f'/dev/{key}'
    def close(self):
        self.closed=True

class HTTP(unittest.TestCase):
    def setUp(self):
        self.cameras=FakeCameras()
        self.server=Workbench(('127.0.0.1',0),cameras=self.cameras)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def post(self,data,token=None,origin=None):
        headers={'Content-Type':'application/json','X-Control-Token':token if token is not None else self.server.token}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.base+'/api/command',data=json.dumps(data).encode(),headers=headers)
        return json.load(self.opener.open(req))
    def test_simulation_state_and_static(self):
        state=json.load(self.opener.open(self.base+'/api/state'))
        self.assertTrue(state['simulation']);self.assertFalse(state['enabled'])
        self.assertEqual(len(state['joints_deg']),6)
        page=self.opener.open(self.base).read().decode()
        self.assertIn(self.server.token,page);self.assertNotIn('__TOKEN__',page)
        self.assertIn('双路现场画面',page)
    def test_camera_frames_are_same_origin(self):
        for key in ('gemini','external'):
            response=self.opener.open(f'{self.base}/api/cameras/{key}/frame.jpg')
            self.assertEqual(response.headers.get_content_type(),'image/jpeg')
            self.assertEqual(response.headers['X-Frame-Id'],'7')
            self.assertEqual(response.read(),b'\xff\xd8test-frame\xff\xd9')
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.opener.open(self.base+'/api/cameras/missing/frame.jpg')
        self.assertEqual(error.exception.code,404);error.exception.close()
    def test_auth_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.post({'action':'enable','client':'x'},token='bad')
        self.assertEqual(e.exception.code,403);self.assertFalse(self.server.controller.enabled);e.exception.close()
    def test_cross_origin_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.post({'action':'enable','client':'x'},origin='https://example.com')
        self.assertEqual(e.exception.code,403);e.exception.close()
    def test_invalid_command_returns_visible_error(self):
        self.post({'action':'enable','client':'x'})
        with self.assertRaises(urllib.error.HTTPError) as e:self.post({'action':'target','client':'x','gripper_mm':90})
        self.assertEqual(e.exception.code,400);self.assertIn('error',json.load(e.exception));e.exception.close()
    def test_no_live_endpoint(self):
        with self.assertRaises(urllib.error.HTTPError) as e:self.opener.open(self.base+'/api/live')
        self.assertEqual(e.exception.code,404);e.exception.close()
    def test_hold_validation_does_not_connect_sdk_or_enable_policy(self):
        server = Workbench(('127.0.0.1', 0), live=True, cameras=FakeCameras(), validate_hold=True)
        try:
            state = server.controller.snapshot()
            self.assertTrue(state['hold_available'])
            self.assertFalse(state['policy_execution_available'])
            self.assertFalse(state['enabled'])
            self.assertIsNone(server.controller.process)
        finally:
            server.server_close()
    def test_explicit_pause_hold_resume_api_in_simulation(self):
        self.post({'action':'enable','client':'x'})
        state=self.post({'action':'pause_hold','client':'x'})
        self.assertEqual(state['control_state'],'holding')
        self.assertTrue(state['enabled']);self.assertTrue(state['hold_available'])
        self.assertFalse(state['hold_is_safety_stop'])
        self.assertEqual(state['hold_target_deg'],state['target_deg'])
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.post({'action':'target','client':'x','gripper_mm':0})
        self.assertEqual(e.exception.code,400);e.exception.close()
        state=self.post({'action':'resume','client':'x'})
        self.assertEqual(state['control_state'],'active')
        state=self.post({'action':'stop','client':'x'})
        self.assertEqual(state['control_state'],'disabled')

if __name__=='__main__':unittest.main()
