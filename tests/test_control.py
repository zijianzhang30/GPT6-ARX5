import math
import unittest
import numpy as np
from control import Controller, Kinematics, LOWER, UPPER, START, LEASE, rotation, rotation_error
from sdk_contract import CommandAdapter, GripperCalibration, FOLLOWER_CONFIG

class Clock:
    t=0.
    def __call__(self):return self.t

class Controls(unittest.TestCase):
    def setUp(self):
        self.clock=Clock();self.c=Controller(self.clock)
        self.cmd(action='enable')
    def cmd(self, **data):return self.c.command({'client':'test',**data})
    def advance(self, seconds, jog=None, grip=0):
        for _ in range(round(seconds/.02)):
            self.cmd(action='heartbeat',jog=jog if jog is not None else [0]*6,gripper=grip)
            self.clock.t+=.02;self.c.tick()
    def test_all_six_joints_both_directions(self):
        for i in range(6):
            for sign in [-1,1]:
                before=self.c.q.copy();v=np.zeros(6);v[i]=sign
                self.advance(.3,v)
                self.assertGreater(sign*(self.c.q[i]-before[i]),.001)
                np.testing.assert_allclose(np.delete(self.c.q,i),np.delete(before,i),atol=1e-9)
                self.advance(.02)
    def test_full_joint_range_reachable(self):
        self.cmd(action='settings',speed=1.)
        for limit in [LOWER,UPPER]:
            self.cmd(action='target',joints_deg=np.degrees(limit).tolist())
            self.advance(15)
            np.testing.assert_allclose(self.c.q,limit,atol=1e-7)
    def test_gripper_full_range(self):
        self.cmd(action='settings',speed=1.)
        for v in [0,80,0]:
            self.cmd(action='target',gripper_mm=v);self.advance(2.2)
            self.assertAlmostEqual(self.c.grip,v)
    def test_gripper_motion_is_reported(self):
        self.advance(.1,grip=1)
        self.assertTrue(self.c.motion)
        self.assertGreater(self.c.grip,40)
    def test_all_cartesian_axes_both_frames(self):
        for frame in ['base','tool']:
            for axis in range(6):
                for sign in [-1,1]:
                    self.c.q=START.copy();self.c.target=START.copy();self.c.velocity[:]=0
                    self.cmd(action='settings',mode='cartesian',frame=frame)
                    before=self.c.kin.fk(self.c.q);v=np.zeros(6);v[axis]=sign
                    self.advance(.12,v)
                    after=self.c.kin.fk(self.c.q)
                    delta=after[:3,3]-before[:3,3] if axis<3 else rotation_error(after[:3,:3],before[:3,:3])
                    if frame=='tool':delta=before[:3,:3].T@delta
                    self.assertGreater(sign*delta[axis%3],1e-5,(frame,axis,sign))
                    self.advance(.02)
    def test_watchdog_cancels_target(self):
        self.cmd(action='target',gripper_mm=80)
        q=self.c.q.copy();self.clock.t+=LEASE+.01;self.c.tick()
        self.assertFalse(self.c.enabled);self.assertEqual(self.c.grip,40)
        np.testing.assert_array_equal(q,self.c.target)
    def test_release_no_queued_motion(self):
        self.advance(.3,[1,0,0,0,0,0]);self.advance(.02)
        q=self.c.q.copy();self.advance(.5)
        np.testing.assert_array_equal(q,self.c.q)
    def test_stop_blocks_future_targets(self):
        self.cmd(action='stop')
        with self.assertRaises(ValueError):self.cmd(action='target',gripper_mm=80)
    def test_invalid_target_atomic(self):
        q=self.c.target.copy()
        for x in [float('nan'),float('inf'),-1,81]:
            with self.assertRaises(ValueError):self.cmd(action='target',joints_deg=[0]*6,gripper_mm=x)
            np.testing.assert_array_equal(q,self.c.target)
    def test_unreachable_pose_rejected(self):
        before=self.c.target.copy()
        with self.assertRaises(ValueError):self.cmd(action='target',pose=[5000,0,0,0,0,0])
        np.testing.assert_array_equal(before,self.c.target)
    def test_owner_is_exclusive(self):
        with self.assertRaises(ValueError):self.c.command({'client':'other','action':'target','gripper_mm':0})
        self.c.command({'client':'other','action':'stop'})
        self.assertFalse(self.c.enabled)
    def test_save_copies_feedback(self):
        self.cmd(action='save_pose',name='测试');saved=self.c.poses[0]['joints_deg'].copy()
        self.advance(.5,[1,0,0,0,0,0]);self.assertEqual(saved,self.c.poses[0]['joints_deg'])

class Model(unittest.TestCase):
    def test_jacobian_matches_finite_difference(self):
        k=Kinematics();q=START.copy();t=k.fk(q);j=k.jacobian(q)
        self.assertEqual(np.linalg.matrix_rank(j),6)
        for i in range(6):
            qq=q.copy();qq[i]+=1e-6;tt=k.fk(qq)
            actual=np.r_[tt[:3,3]-t[:3,3],rotation_error(tt[:3,:3],t[:3,:3])]/1e-6
            np.testing.assert_allclose(actual,j[:,i],atol=1e-6)
    def test_ik_fk_roundtrip(self):
        k=Kinematics();rng=np.random.default_rng(8)
        for _ in range(12):
            q=START+rng.uniform(-.12,.12,6);t=k.fk(q);solution=k.solve(t,START)
            np.testing.assert_allclose(k.fk(solution),t,atol=3e-4)
    def test_rotation_pi(self):
        r=rotation([1,0,0],math.pi)
        self.assertAlmostEqual(np.linalg.norm(rotation_error(r,np.eye(3))),math.pi)

class FakeArm:
    def __init__(self):self.commands=[]
    def set_joint_positions(self,positions):self.commands.append(('joint',positions))
    def set_catch_pos(self,pos):self.commands.append(('grip',pos))
    def get_joint_positions(self):return [0,1,1,0,0,0,.4]

class Protocol(unittest.TestCase):
    def test_six_radian_targets_and_separate_gripper(self):
        arm=FakeArm();a=CommandAdapter(arm,GripperCalibration(0,4,0,.8))
        a.joints(START);a.grip(40)
        self.assertEqual(len(arm.commands[0][1]),6)
        self.assertEqual(arm.commands[1],('grip',2.))
        self.assertEqual(a.read()['gripper_mm'],40.)
        self.assertEqual(FOLLOWER_CONFIG['type'],0)
    def test_no_invented_gripper_ratio(self):
        arm=FakeArm();a=CommandAdapter(arm)
        with self.assertRaises(ValueError):a.grip(40)
        self.assertEqual(arm.commands,[])
    def test_out_of_range_never_reaches_sdk(self):
        arm=FakeArm();a=CommandAdapter(arm)
        with self.assertRaises(ValueError):a.joints(UPPER+.1)
        self.assertEqual(arm.commands,[])

if __name__=='__main__':unittest.main()
