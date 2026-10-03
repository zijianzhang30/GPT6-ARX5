"""R5 kinematics and deterministic offline controller. No CAN or SDK imports."""
from pathlib import Path
import math
import time
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parent
URDF = ROOT / 'vendor/R5-master/py/ARX_R5_python/bimanual/script/X5liteaa0.urdf'
# Pinned x86_64 vendor SDK constructor bounds, NOT the placeholder URDF limits.
LOWER = np.array([-3.14, -.1, -.1, -1.29, -math.radians(85), -math.radians(100)])
UPPER = np.array([2.618, 3.6, 3.0, 1.29, math.radians(85), math.radians(100)])
START = np.array([0., .8, 1.2, .3, .4, .1])
LEASE = .35


def vector(value, n):
    try:
        a = np.asarray(value, dtype=float)
    except (ValueError, TypeError):
        raise ValueError('请输入有效数字') from None
    if a.shape != (n,) or not np.isfinite(a).all():
        raise ValueError(f'需要 {n} 个有限数值')
    return a


def rotation(axis, angle):
    a = np.asarray(axis, dtype=float)
    a /= np.linalg.norm(a)
    x, y, z = a
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle) * k + (1-math.cos(angle)) * k @ k


def rpy_matrix(rpy):
    r, p, y = rpy
    return rotation([0, 0, 1], y) @ rotation([0, 1, 0], p) @ rotation([1, 0, 0], r)


def matrix_rpy(r):
    p = math.atan2(-r[2, 0], math.hypot(r[0, 0], r[1, 0]))
    if abs(math.cos(p)) < 1e-7:
        return np.array([0., p, math.atan2(-r[0, 1], r[1, 1])])
    return np.array([math.atan2(r[2, 1], r[2, 2]), p, math.atan2(r[1, 0], r[0, 0])])


def rotation_error(target, current):
    r = target @ current.T
    theta = math.acos(float(np.clip((np.trace(r)-1)/2, -1, 1)))
    v = np.array([r[2, 1]-r[1, 2], r[0, 2]-r[2, 0], r[1, 0]-r[0, 1]])
    if theta < 1e-6:
        return v / 2
    if math.pi-theta < 1e-5:
        values, axes = np.linalg.eigh((r + np.eye(3))/2)
        axis = axes[:, np.argmax(values)]
        if np.dot(axis, v) < 0:
            axis = -axis
        return axis * theta
    return v * theta / (2*math.sin(theta))


class PauseProfile:
    """Analytic command-space deceleration; not a physical braking guarantee."""
    def __init__(self, q, velocity):
        self.origin = vector(q, 6).copy()
        self.initial_velocity = vector(velocity, 6).copy()
        self.deceleration = math.radians(120)
        self.stop_times = np.abs(self.initial_velocity)/self.deceleration
        self.duration = float(np.max(self.stop_times))
        self.goal = (self.origin + self.initial_velocity*self.stop_times/2)
        if (np.any(self.origin < LOWER) or np.any(self.origin > UPPER)
                or np.any(self.goal < LOWER) or np.any(self.goal > UPPER)):
            raise ValueError('暂停减速轨迹超出关节范围；不能进入保持')

    def sample(self, elapsed):
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('Invalid pause profile time')
        t = np.minimum(elapsed, self.stop_times)
        sign = np.sign(self.initial_velocity)
        q = self.origin + self.initial_velocity*t - sign*self.deceleration*t*t/2
        v = sign*np.maximum(np.abs(self.initial_velocity)-self.deceleration*t, 0)
        return q, v


class Kinematics:
    def __init__(self):
        self.joints = []
        for j in ET.parse(URDF).getroot().findall('joint'):
            if j.attrib['type'] != 'revolute':
                continue
            origin = j.find('origin')
            xyz = np.fromstring(origin.attrib['xyz'], sep=' ')
            rpy = np.fromstring(origin.attrib.get('rpy', '0 0 0'), sep=' ')
            axis = np.fromstring(j.find('axis').attrib['xyz'], sep=' ')
            self.joints.append((xyz, rpy_matrix(rpy), axis))
        if len(self.joints) != 6:
            raise ValueError('R5 模型必须包含 6 个转动关节')

    def frames(self, q):
        t = np.eye(4)
        frames, axes, points = [], [], [np.zeros(3)]
        for angle, (xyz, r, axis) in zip(q, self.joints):
            origin = np.eye(4)
            origin[:3, :3], origin[:3, 3] = r, xyz
            t = t @ origin
            points.append(t[:3, 3].copy())
            axes.append(t[:3, :3] @ axis)
            turn = np.eye(4)
            turn[:3, :3] = rotation(axis, float(angle))
            t = t @ turn
            frames.append(t.copy())
        return t, np.array(points), axes, frames

    def fk(self, q):
        return self.frames(q)[0]

    def jacobian(self, q):
        t, points, axes, _ = self.frames(q)
        return np.array([np.r_[np.cross(a, t[:3, 3]-p), a]
                         for a, p in zip(axes, points[1:])]).T

    def solve(self, target, seed, attempts=1):
        seeds = [np.array(seed, dtype=float)]
        if attempts > 1:
            seeds += [START.copy(), (LOWER + UPPER)/2]
        for q in seeds:
            for _ in range(100):
                actual = self.fk(q)
                error = np.r_[target[:3, 3]-actual[:3, 3],
                              rotation_error(target[:3, :3], actual[:3, :3])]
                if np.linalg.norm(error[:3]) < 2e-5 and np.linalg.norm(error[3:]) < 2e-4:
                    return q
                weights = np.array([1, 1, 1, .15, .15, .15])
                j = self.jacobian(q) * weights[:, None]
                e = error * weights
                dq = j.T @ np.linalg.solve(j @ j.T + .00002*np.eye(6), e)
                q = np.clip(q + np.clip(dq, -.12, .12), LOWER, UPPER)
        raise ValueError('此位姿不可达、接近奇异点或超出关节范围；目标未改变')


class Controller:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.kin = Kinematics()
        self.q = START.copy()
        self.target = self.q.copy()
        self.velocity = np.zeros(6)
        self.grip = self.grip_target = 40.
        self.enabled = False
        self.speed = .25
        self.mode = 'joint'
        self.frame = 'base'
        self.jog = np.zeros(6)
        self.grip_jog = 0.
        self.owner = None
        self.last_beat = 0.
        self.last_tick = clock()
        self.message = '离线模拟已就绪。启用控制后，按住按键或按钮移动。'
        self.events = []
        self.motion = False
        self.poses = []
        self.hold_available = True
        self.pause_profile = None
        self.pause_elapsed = 0.

    @property
    def control_state(self):
        if not self.enabled:
            return 'disabled'
        if self.pause_profile is None:
            return 'active'
        return 'holding' if self.pause_elapsed >= self.pause_profile.duration else 'pausing'

    def pause_origin(self):
        return self.q

    def pause_hold(self):
        if not self.hold_available:
            raise ValueError('暂停保持尚未通过实机验证，当前不可用')
        if not self.enabled:
            raise ValueError('请先启用控制；暂停保持不会自动使能')
        if self.pause_profile is not None:
            return  # Repeated requests must not relatch a drifting encoder value.
        try:
            profile = PauseProfile(self.pause_origin(), self.velocity)
        except ValueError:
            self.stop('无法生成关节范围内的暂停轨迹，已停止原动作')
            raise
        self.pause_profile = profile
        self.pause_elapsed = 0.
        self.target = profile.goal.copy()
        self.grip_target = self.grip
        self.jog[:] = 0
        self.grip_jog = 0
        self.note('暂停保持：旧轨迹已取消；仍处于使能状态，需持续心跳')

    def resume(self):
        if self.control_state != 'holding':
            raise ValueError('只有完成减速并保持后才能恢复')
        self.target = self.pause_profile.goal.copy()
        self.pause_profile = None
        self.pause_elapsed = 0.
        self.velocity[:] = 0
        self.note('已恢复接收新动作；不会继续暂停前的轨迹')

    def note(self, text):
        self.message = text
        if not self.events or self.events[-1]['message'] != text:
            self.events.append({'time': time.strftime('%H:%M:%S'), 'message': text})
            self.events = self.events[-30:]

    def stop(self, text='已暂停，后续移动已取消'):
        self.pause_profile = None
        self.pause_elapsed = 0.
        self.target = self.q.copy()
        self.grip_target = self.grip
        self.velocity[:] = 0
        self.jog[:] = 0
        self.grip_jog = 0
        self.enabled = self.motion = False
        self.owner = None
        self.note(text)

    def command(self, data):
        action = data.get('action')
        client = data.get('client', '')
        if not isinstance(client, str) or len(client) > 100:
            raise ValueError('无效控制端')
        if action == 'stop':
            self.stop()
            return
        if self.enabled and self.owner != client:
            raise ValueError('另一个窗口正在控制。可先按暂停接管。')
        if self.pause_profile is not None and action not in ('heartbeat', 'pause_hold', 'resume'):
            raise ValueError('暂停保持中；请明确恢复后再发送新动作')
        if action == 'pause_hold':
            self.pause_hold()
            self.last_beat = self.clock()
        elif action == 'resume':
            self.resume()
            self.last_beat = self.clock()
        elif action == 'enable':
            if not client:
                raise ValueError('缺少控制端标识')
            self.target, self.grip_target = self.q.copy(), self.grip
            self.owner, self.enabled, self.last_beat = client, True, self.clock()
            self.note('控制已启用；松开即停，空格暂停')
        elif action == 'heartbeat':
            if self.enabled:
                jog = vector(data.get('jog', [0]*6), 6)
                gj = float(vector([data.get('gripper', 0)], 1)[0])
                if np.max(np.abs(jog)) > 1 or abs(gj) > 1:
                    raise ValueError('点动方向必须在 -1 至 1 之间')
                if self.pause_profile is not None and (np.any(jog) or gj):
                    raise ValueError('暂停保持中不能点动；请先明确恢复')
                if (np.any(self.jog) or self.grip_jog) and not np.any(jog) and not gj:
                    self.target, self.grip_target = self.q.copy(), self.grip
                    self.velocity[:] = 0
                self.jog, self.grip_jog = jog, gj
                self.last_beat = self.clock()
        elif action == 'settings':
            speed = float(vector([data.get('speed', self.speed)], 1)[0])
            mode, frame = data.get('mode', self.mode), data.get('frame', self.frame)
            if not .05 <= speed <= 1 or mode not in ('joint', 'cartesian') or frame not in ('base', 'tool'):
                raise ValueError('无效控制设置')
            if mode != self.mode or frame != self.frame:
                self.target, self.grip_target = self.q.copy(), self.grip
                self.jog[:] = 0
                self.grip_jog = 0
                self.velocity[:] = 0
            self.speed, self.mode, self.frame = speed, mode, frame
        elif action == 'target':
            if not self.enabled:
                raise ValueError('请先启用控制')
            q, grip = self.target.copy(), self.grip_target
            if 'joints_deg' in data:
                q = np.radians(vector(data['joints_deg'], 6))
            if 'pose' in data:
                pose = vector(data['pose'], 6)
                t = np.eye(4)
                t[:3, 3], t[:3, :3] = pose[:3]/1000, rpy_matrix(np.radians(pose[3:]))
                q = self.kin.solve(t, self.q, attempts=3)
            if 'gripper_mm' in data:
                grip = float(vector([data['gripper_mm']], 1)[0])
            if np.any(q < LOWER-1e-9) or np.any(q > UPPER+1e-9):
                raise ValueError('目标超出 SDK 关节范围')
            if not 0 <= grip <= 80:
                raise ValueError('夹爪开口范围为 0–80 mm（模拟）')
            self.target, self.grip_target = q, grip
            self.last_beat = self.clock()
            self.note('目标已接收，按设定速度平滑移动')
        elif action == 'reset':
            if self.enabled:
                raise ValueError('请先暂停再重置模拟')
            self.q = self.target = START.copy()
            self.grip = self.grip_target = 40.
            self.note('模拟已重置')
        elif action == 'save_pose':
            name = str(data.get('name', '')).strip()[:40] or f'位置 {len(self.poses)+1}'
            if len(self.poses) >= 20:
                raise ValueError('最多保存 20 个位置，请先删除一些')
            self.poses.append({'name': name, 'joints_deg': np.degrees(self.q).tolist(), 'gripper_mm': self.grip})
            self.note(f'已保存「{name}」')
        elif action == 'delete_pose':
            i = data.get('index')
            if not isinstance(i, int) or not 0 <= i < len(self.poses):
                raise ValueError('位置不存在')
            self.poses.pop(i)
        else:
            raise ValueError('未知操作')

    def tick(self):
        now = self.clock()
        dt = max(0., min(now-self.last_tick, .05))
        self.last_tick = now
        if not self.enabled:
            return
        if now-self.last_beat > LEASE:
            self.stop('控制连接超时，已暂停；重新启用后继续')
            return
        if self.pause_profile is not None:
            self.pause_elapsed += dt
            self.q, self.velocity = self.pause_profile.sample(self.pause_elapsed)
            self.motion = bool(np.any(np.abs(self.velocity) > 1e-7))
            return
        if np.any(self.jog):
            if self.mode == 'joint':
                proposed = self.q + self.jog * math.radians(30) * self.speed * dt
                self.target = np.clip(proposed, LOWER, UPPER)
                if np.any(proposed != self.target):
                    self.note('已到达关节范围边界')
            else:
                t = self.kin.fk(self.q)
                delta = self.jog[:3] * .10 * self.speed * dt
                angular = self.jog[3:] * math.radians(30) * self.speed * dt
                length = np.linalg.norm(angular)
                change = rotation(angular, length) if length > 1e-10 else np.eye(3)
                if self.frame == 'tool':
                    t[:3, 3] += t[:3, :3] @ delta
                    t[:3, :3] = t[:3, :3] @ change
                else:
                    t[:3, 3] += delta
                    t[:3, :3] = change @ t[:3, :3]
                try:
                    self.target = self.kin.solve(t, self.q)
                except ValueError as e:
                    self.target = self.q.copy()
                    self.note(str(e))
        if self.grip_jog:
            self.grip_target = float(np.clip(self.grip + self.grip_jog*40*self.speed*dt, 0, 80))
        error = self.target-self.q
        max_velocity = math.radians(30)*self.speed
        desired = np.clip(error/max(dt, .001), -max_velocity, max_velocity)
        acceleration = math.radians(120)*dt
        self.velocity += np.clip(desired-self.velocity, -acceleration, acceleration)
        step = self.velocity*dt
        step = np.where(np.abs(step)>np.abs(error), error, step)
        new_q = np.clip(self.q+step, LOWER, UPPER)
        self.velocity = (new_q-self.q)/max(dt, .001)
        self.q = new_q
        grip_step = float(np.clip(self.grip_target-self.grip, -40*self.speed*dt, 40*self.speed*dt))
        self.grip += grip_step
        self.motion = bool(np.max(np.abs(step))>1e-7 or abs(grip_step)>.001)

    def snapshot(self):
        t, points, _, frames = self.kin.frames(self.q)
        tt = self.kin.fk(self.target)
        singular_values = np.linalg.svd(self.kin.jacobian(self.q), compute_uv=False)
        return {'simulation': True, 'enabled': self.enabled, 'moving': self.motion,
                'control_state': self.control_state, 'hold_available': self.hold_available,
                'hold_is_safety_stop': False,
                'hold_target_deg': np.degrees(self.pause_profile.goal).tolist() if self.pause_profile else None,
                'mode': self.mode, 'frame': self.frame, 'speed': self.speed,
                'joints_deg': np.degrees(self.q).tolist(), 'target_deg': np.degrees(self.target).tolist(),
                'velocity_deg': np.degrees(self.velocity).tolist(),
                'lower_deg': np.degrees(LOWER).tolist(), 'upper_deg': np.degrees(UPPER).tolist(),
                'pose': np.r_[t[:3, 3]*1000, np.degrees(matrix_rpy(t[:3, :3]))].tolist(),
                'target_pose': np.r_[tt[:3, 3]*1000, np.degrees(matrix_rpy(tt[:3, :3]))].tolist(),
                'gripper_mm': self.grip, 'gripper_target_mm': self.grip_target,
                'points': points.tolist(), 'frames': [f.tolist() for f in frames],
                'near_singular': bool(singular_values[-1] < .008),
                'message': self.message, 'events': self.events, 'poses': self.poses,
                'owner': self.owner, 'lease_ms': round(LEASE*1000)}
