import unittest,time
import numpy as np
from live_control import LiveController
from control import START
class Live(unittest.TestCase):
    def setUp(self):
        self.c=LiveController();self.sent=[];self.c.send=self.sent.append
    def feed(self,q=None,age=0.,sample_age=0.,errors=None):
        self.c.robot_status='waiting'
        self.c.inbox.put({'status':'feedback','q':list(START if q is None else q)+[.7],
          'velocity':[.01]*7,'current':[.1]*7,'sample_time':time.monotonic()-sample_age,
          'rx_age':age,'rx_count':23,'rx_ids':[1,2,3,4,5,6,7],'error_codes':errors or [],'fault':False})
        self.c.tick()
    def cmd(self,**kw):self.c.command({'client':'test',**kw})
    def test_no_fabricated_pose_before_connection(self):
        s=self.c.snapshot();self.assertFalse(s['simulation']);self.assertFalse(s['model_ready'])
        self.assertEqual(s['points'],[]);self.assertEqual(s['joints_deg'],[None]*6)
    def test_supervised_mode_still_requires_measured_hold_and_stop_clears_it(self):
        self.c=LiveController(supervised_policy=True);self.c.send=self.sent.append
        self.feed();self.cmd(action='enable')
        self.assertFalse(self.c.snapshot()['policy_execution_available'])
        self.c.policy_gate.qualified_owner='test'
        self.assertTrue(self.c.snapshot()['policy_execution_available'])
        self.cmd(action='stop')
        self.assertFalse(self.c.snapshot()['policy_execution_available'])
        self.cmd(action='enable')
        self.assertFalse(self.c.snapshot()['policy_execution_available'])
    def test_measured_feedback_drives_geometry(self):
        self.feed();s=self.c.snapshot();self.assertTrue(s['model_ready'])
        np.testing.assert_allclose(s['joints_deg'],np.degrees(START))
        np.testing.assert_allclose(s['points'][-1],self.c.kin.fk(START)[:3,3])
        self.assertEqual(s['gripper_raw'],.7);self.assertIsNone(s['gripper_mm'])
    def test_target_does_not_fake_measured_position(self):
        self.feed();self.cmd(action='enable')
        self.cmd(action='target',joints_deg=np.degrees(START+.02).tolist())
        self.c.last_tick-=.02;self.c.tick()
        np.testing.assert_allclose(self.c.q,START)
        self.assertTrue(any(m['action']=='target' for m in self.sent))
    def advance(self,steps=1):
        for _ in range(steps):
            self.c.feedback_at=time.monotonic();self.c.last_beat=time.monotonic()
            self.c.last_tick=self.c.clock()-.02;self.c.tick()
    def test_lagging_joint_command_accumulates_but_is_bounded(self):
        self.feed();self.cmd(action='enable')
        goal=START.copy();goal[2]+=.5
        self.cmd(action='target',joints_deg=np.degrees(goal).tolist())
        self.advance(60)
        self.assertGreater(self.c.command_q[2]-START[2],np.radians(2.9))
        self.assertLessEqual(self.c.command_q[2]-START[2],np.radians(3.)+1e-9)
        self.assertTrue(self.c.snapshot()['tracking_limited'])
        np.testing.assert_allclose(self.c.q,START)
        self.assertAlmostEqual(self.c.snapshot()['command_deg'][2],np.degrees(self.sent[-1]['q'][2]))
    def test_release_discards_jog_lead(self):
        self.feed();self.cmd(action='enable')
        self.cmd(action='heartbeat',jog=[0,0,1,0,0,0]);self.advance(15)
        self.assertGreater(self.c.command_q[2],START[2])
        self.cmd(action='heartbeat',jog=[0]*6);self.advance()
        np.testing.assert_allclose(self.sent[-1]['q'],START)
    def test_following_motor_can_reach_goal_beyond_lead_limit(self):
        self.feed();self.cmd(action='enable')
        goal=START.copy();goal[2]+=.2
        self.cmd(action='target',joints_deg=np.degrees(goal).tolist())
        for _ in range(160):
            self.advance()
            self.c.q+=.2*(self.c.command_q-self.c.q)
        self.assertLess(abs(self.c.q[2]-goal[2]),.001)
    def test_lease_expiry_restores_measured_target(self):
        self.feed();self.cmd(action='enable')
        self.cmd(action='target',joints_deg=np.degrees(START+.1).tolist());self.advance(5)
        self.c.last_beat-=1;self.c.tick()
        self.assertFalse(self.c.enabled)
        np.testing.assert_allclose(self.c.target,self.c.q)
        np.testing.assert_allclose(self.c.command_q,self.c.q)
    def test_stale_feedback_blocks_motion(self):
        self.feed(age=1.)
        with self.assertRaises(ValueError):self.cmd(action='enable')
    def test_stale_worker_sample_not_freshened(self):
        self.feed(sample_age=2.)
        self.assertEqual(self.c.robot_status,'fault')
    def test_raw_gripper_command(self):
        self.feed();self.cmd(action='enable');self.cmd(action='target',gripper_raw=1.2)
        self.c.last_tick-=.02;self.c.tick();last=self.sent[-1]
        self.assertGreater(last['grip'],.8);self.assertLess(last['grip'],1.2)
    def test_supervised_opening_is_five_times_faster_with_original_closing_rate(self):
        self.c=LiveController(supervised_policy=True);self.c.send=self.sent.append
        self.feed();self.c.speed=.3;self.cmd(action='enable')
        before=self.c.last_grip
        self.cmd(action='target',gripper_raw=1.2);self.advance()
        self.assertAlmostEqual(self.c.last_grip-before, .018)
        self.assertEqual(self.c.snapshot()['gripper_open_speed_multiplier'],5.)
        np.testing.assert_allclose(self.sent[-1]['q'],START)
        self.assertEqual(self.c.gripper_raw,.7)
        before=self.c.last_grip
        self.cmd(action='target',gripper_raw=.2);self.advance()
        self.assertAlmostEqual(before-self.c.last_grip,.0036)
    def test_fast_opening_never_overshoots_or_bypasses_lease_expiry(self):
        self.c=LiveController(supervised_policy=True);self.c.send=self.sent.append
        self.feed();self.c.speed=.3;self.cmd(action='enable')
        self.cmd(action='target',gripper_raw=.805);self.advance()
        self.assertAlmostEqual(self.c.last_grip,.805)
        self.cmd(action='target',gripper_raw=4.8)
        self.c.last_beat-=1;self.c.tick()
        self.assertFalse(self.c.enabled)
        self.assertEqual(self.sent[-1],{'action':'pause'})
    def test_nonpolicy_opening_keeps_the_original_rate(self):
        self.feed();self.c.speed=.3;self.cmd(action='enable')
        before=self.c.last_grip
        self.cmd(action='target',gripper_raw=1.2);self.advance()
        self.assertAlmostEqual(self.c.last_grip-before,.0036)
        self.assertEqual(self.c.snapshot()['gripper_open_speed_multiplier'],1.)
    def test_enable_never_clips_manually_displaced_gripper(self):
        for feedback in (5.207522869110107, 4.95, -0.01, None, True, float('nan'), float('inf')):
            with self.subTest(feedback=feedback):
                self.setUp();self.feed();self.c.gripper_raw=feedback
                self.c.raw_target=.336;self.c.last_grip=.236
                with self.assertRaises(ValueError):self.cmd(action='enable')
                self.assertFalse(self.c.enabled);self.assertIsNone(self.c.owner)
                self.assertEqual(self.c.raw_target,.336);self.assertEqual(self.c.last_grip,.236)
                self.assertEqual(self.sent,[])
    def test_rejected_enable_does_not_mutate_gripper_reference(self):
        self.feed();self.c.raw_target=1.2;self.c.last_grip=1.1
        with self.assertRaises(ValueError):self.c.command({'action':'enable','client':''})
        self.assertFalse(self.c.enabled)
        self.assertEqual(self.c.raw_target,1.2);self.assertEqual(self.c.last_grip,1.1)
        self.assertEqual(self.sent,[])
    def test_millimetres_are_not_sent_as_raw(self):
        self.feed();self.cmd(action='enable')
        with self.assertRaises(ValueError):self.cmd(action='target',gripper_mm=40)
    def test_fault_codes_disable(self):
        self.feed(errors=[11]);self.assertEqual(self.c.robot_status,'fault')
    def test_stop_requests_native_protection(self):
        self.feed();self.cmd(action='enable');self.cmd(action='stop')
        self.assertEqual(self.sent[-1],{'action':'pause'});self.assertFalse(self.c.enabled)
    def test_connect_requires_explicit_init_ack(self):
        with self.assertRaises(ValueError):self.cmd(action='connect')
        self.assertIsNone(self.c.process)
if __name__=='__main__':unittest.main()
