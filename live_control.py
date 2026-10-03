"""Measured-state controller with an isolated vendor SDK process."""
import json,os,queue,subprocess,sys,threading,time
from pathlib import Path
import numpy as np
from control import Controller,ROOT,LOWER,UPPER,LEASE,vector
from motion_safety import (finite, SUPERVISED_SPEED, POLICY_HOLD_ERROR_DEG,
                           POLICY_SETTLE_ERROR_DEG, POLICY_TRACKING_ERROR_DEG,
                           JOINT_STEP_DEG, JOINT_STEP_NORM_DEG,
                           GRIPPER_OPEN_SPEED_MULTIPLIER)
from policy_hold_gate import PolicyHoldGate
from policy_trajectory import PolicyTrajectory

class LiveController(Controller):
    def __init__(self,channel='can0',*,experimental_hold=False,supervised_policy=False):
        super().__init__()
        # Explicit host validation mode permits empty-arm tests, not policy execution.
        self.hold_available=experimental_hold or supervised_policy
        self.supervised_policy=supervised_policy
        self.policy_gate=PolicyHoldGate()
        self.policy_trajectory=None
        self.channel=channel;self.process=None;self.inbox=queue.Queue()
        self.command_q=self.q.copy()
        self.max_tracking_error=np.radians(POLICY_TRACKING_ERROR_DEG)
        self.tracking_limited=False
        self.robot_status='disconnected';self.feedback_at=0.;self.rx_age=None
        self.rx_count=0;self.rx_ids=[];self.error_codes=[];self.currents=[0.]*7;self.robot_velocity=np.zeros(6)
        self.gripper_raw=None;self.raw_target=None;self.last_grip=None;self.log=None
        self.worker_fault_reason=None
        self.worker_protocol_version=None
        self.note('实机模式：点击「连接机械臂」开始 SDK 初始化。初始化包含电机回零。')
    def send(self,msg):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(json.dumps(msg)+'\n');self.process.stdin.flush()
            except (BrokenPipeError,OSError):
                self.enabled=False;self.robot_status='fault';self.note('SDK 通信进程已断开')
    def connect(self):
        if self.process and self.process.poll() is None:raise ValueError('连接已启动，请等待当前初始化完成')
        if not Path('/sys/class/net',self.channel).exists():raise ValueError(f'{self.channel} 不存在；重新插入适配器后先运行 ./connect_can.sh')
        env=os.environ.copy();base=ROOT/'vendor/R5-master/py/ARX_R5_python/bimanual/api'
        env['LD_LIBRARY_PATH']=':'.join([str(ROOT/'kdl_local/lib'),str(base/'arx_r5_src'),str(base),env.get('LD_LIBRARY_PATH','')])
        while not self.inbox.empty():self.inbox.get()
        self.feedback_at=0.;self.rx_age=None;self.gripper_raw=None
        self.worker_fault_reason=None
        self.worker_protocol_version=None
        self.policy_gate.reset()
        self.log=open(ROOT/'robot.log','a',buffering=1)
        self.process=subprocess.Popen([sys.executable,'-u',str(ROOT/'robot_worker.py'),self.channel],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,env=env,cwd=ROOT)
        process=self.process
        def read():
            for line in process.stdout:
                try:self.inbox.put(json.loads(line))
                except ValueError:pass
            self.inbox.put({'status':'exited','message':f'SDK 进程已结束（{process.wait()}），查看 robot.log'})
        threading.Thread(target=read,daemon=True).start()
        self.robot_status='initializing';self.note('正在初始化真实机械臂，SDK 可能回零；请等待反馈。')
    def stop(self,text='已请求 SDK 保护模式；这不是物理急停'):
        self.policy_trajectory=None
        self.policy_gate.reset()
        super().stop(text)
        self.command_q=self.q.copy();self.tracking_limited=False
        self.send({'action':'pause'})
    def pause_origin(self):
        return self.command_q
    def hold_feedback_healthy(self):
        return (self.robot_status=='ready' and 0<=time.monotonic()-self.feedback_at<=.15
                and self.rx_age is not None and np.isfinite(self.rx_age) and 0<=self.rx_age<=.15
                and not self.error_codes and np.isfinite(self.q).all()
                and np.all(self.q>=LOWER) and np.all(self.q<=UPPER))
    def hold_tracking_healthy(self,limit):
        return (not self.tracking_limited and np.isfinite(self.command_q).all()
                and np.isfinite(self.q).all()
                and np.max(np.abs(self.command_q-self.q))<=limit)
    def pause_hold(self):
        if not self.hold_available:
            raise ValueError('暂停保持尚未通过实机验证，当前不可用')
        if not self.enabled:
            raise ValueError('请先启用控制；暂停保持不会自动使能')
        self.policy_trajectory=None
        if (not self.hold_feedback_healthy()
                or not self.hold_tracking_healthy(np.radians(POLICY_HOLD_ERROR_DEG))):
            self.stop('无法进入暂停保持，已请求 SDK 保护模式')
            raise ValueError('实机反馈或跟随状态不满足暂停保持条件')
        already_paused=self.pause_profile is not None
        super().pause_hold()
        if not already_paused:
            # Keep the last issued gripper command, not a guessed force/width.
            self.raw_target=self.last_grip
    def command(self,data):
        action=data.get('action')
        pending_raw=None
        enable_raw=None
        was_jogging=bool(np.any(self.jog) or self.grip_jog)
        old_mode,old_frame=self.mode,self.frame
        if self.enabled and self.owner!=data.get('client') and action not in ('stop','disconnect'):
            raise ValueError('另一个窗口正在控制')
        if self.policy_trajectory is not None and action not in ('heartbeat','pause_hold','stop','disconnect'):
            raise ValueError('Timed policy trajectory active; hold or stop before another command')
        if (self.policy_trajectory is not None and action=='heartbeat'
                and (any(data.get('jog',[0]*6)) or data.get('gripper',0))):
            raise ValueError('Jogging cannot modify an active policy trajectory')
        if self.pause_profile is not None:
            if action not in ('heartbeat','pause_hold','resume','stop','disconnect'):
                raise ValueError('暂停保持中；请明确恢复后再发送新动作')
            if action=='resume' and (not self.hold_feedback_healthy()
                                    or not self.hold_tracking_healthy(np.radians(POLICY_HOLD_ERROR_DEG))):
                self.stop('无法恢复保持状态，已请求 SDK 保护模式')
                raise ValueError('反馈不健康，不能恢复')
        if action=='heartbeat' and self.grip_jog and not data.get('gripper',0):
            self.raw_target=self.last_grip
        if action=='save_pose':
            raise ValueError('实机位置保存尚未启用；请先完成控制验证')
        if action=='policy_trajectory':
            if (not self.supervised_policy or not self.policy_gate.available(self.owner,self.enabled)
                    or self.mode!='joint' or self.speed!=SUPERVISED_SPEED or not self.hold_feedback_healthy()
                    or not self.hold_tracking_healthy(np.radians(POLICY_HOLD_ERROR_DEG))):
                raise ValueError('Qualified supervised joint control is required')
            now=time.monotonic()
            issued=data.get('issued_at')
            if not finite(issued) or not 0<=now-issued<=.15:
                raise ValueError('Expired trajectory request')
            start=vector(data.get('start_deg'),6)
            if np.max(np.abs(start-np.degrees(self.q)))>POLICY_HOLD_ERROR_DEG:
                raise ValueError('Trajectory start exceeds the qualified hold residual')
            if np.max(np.abs(start-np.degrees(self.command_q)))>.05:
                raise ValueError('Trajectory start would jump from the held command')
            plan=PolicyTrajectory(start.tolist(),data.get('points_deg'),data.get('times_s'),
                                  np.degrees(LOWER).tolist(),np.degrees(UPPER).tolist(),now)
            self.policy_trajectory=plan
            self.target=np.radians(plan.points[-1])
            self.last_beat=self.clock()
            return
        if action=='connect':
            if data.get('acknowledge_initialization') is not True:raise ValueError('请确认 SDK 初始化可能使机械臂回零')
            self.connect();return
        if action=='disconnect':
            self.stop();self.send({'action':'shutdown'});self.robot_status='disconnecting';return
        if action=='reset':raise ValueError('实机模式没有模拟重置；不会自动回零')
        if action in ('enable','target'):
            if self.robot_status!='ready' or time.monotonic()-self.feedback_at>.3 or self.rx_age is None or self.rx_age>.5:raise ValueError('尚未取得新鲜的机械臂反馈，不能移动')
            if np.any(self.q<LOWER-.02) or np.any(self.q>UPPER+.02):raise ValueError('实际关节超出本版 SDK 范围，需要核对零位')
        if action=='target' and 'gripper_raw' in data:
            raw=float(vector([data['gripper_raw']],1)[0])
            if not 0<=raw<=5:raise ValueError('夹爪 SDK 目标范围为 0–5，非毫米')
            if not self.enabled:raise ValueError('请先启用控制')
            if self.owner!=data.get('client'):raise ValueError('另一个窗口正在控制')
            pending_raw=raw
            data={**data};data.pop('gripper_raw')
        if action=='target' and 'gripper_mm' in data:raise ValueError('实机夹爪尚未标定毫米映射，请使用 SDK 原始单位')
        if action=='enable':
            # Reject an unrepresentable initial reference; clipping can move a
            # manually displaced gripper as soon as position control resumes.
            if not finite(self.gripper_raw) or not 0<=self.gripper_raw<=5:
                raise ValueError('夹爪反馈无法映射为已验证的使能目标；请先核对标定，不会自动截断或闭合')
            enable_raw=self.gripper_raw+.1
            if not 0<=enable_raw<=5:
                raise ValueError('夹爪初始目标超出命令范围；请先核对标定，不会自动截断或闭合')
        super().command(data)
        if action=='enable':self.policy_gate.reset()
        if enable_raw is not None:
            self.raw_target=enable_raw;self.last_grip=enable_raw
        released=action=='heartbeat' and was_jogging and not np.any(self.jog) and not self.grip_jog
        changed_frame=action=='settings' and (old_mode!=self.mode or old_frame!=self.frame)
        if action=='enable' or released or changed_frame:
            self.command_q=self.q.copy();self.velocity[:]=0;self.tracking_limited=False
        if pending_raw is not None:self.raw_target=pending_raw
    def tick(self):
        while not self.inbox.empty():
            message=self.inbox.get();status=message.get('status')
            if status=='feedback':
                try:
                    values=vector(message['q'],7);vel=vector(message['velocity'],7);cur=vector(message['current'],7)
                    self.q=values[:6];self.gripper_raw=float(values[6]);self.robot_velocity=vel[:6]
                    self.currents=cur.tolist();self.feedback_at=float(message.get('sample_time',time.monotonic()))
                    self.error_codes=message.get('error_codes',[])
                    self.worker_fault_reason=message.get('fault_reason')
                    self.worker_protocol_version=message.get('worker_protocol_version')
                    self.rx_age=message['rx_age'];self.rx_count=message['rx_count'];self.rx_ids=message['rx_ids']
                    if self.robot_status in ('initializing','waiting'):
                        self.target=self.q.copy();self.robot_status='ready';self.note('已收到实机反馈。网页模型跟随真实关节；点击启用控制后操作。')
                    if message.get('fault') or self.rx_age>.5 or any(code>10 for code in self.error_codes):
                        if self.enabled:self.stop('机械臂反馈超时或 SDK 报错，已请求保护模式')
                        self.robot_status='fault'
                except (ValueError,KeyError):self.stop('无效反馈，已暂停');self.robot_status='fault'
            elif status=='ready':self.robot_status='waiting'
            elif status in ('error','exited','closed'):
                self.enabled=False;self.owner=None;self.robot_status='disconnected' if status=='closed' else 'fault';self.note(message.get('message','实机已断开'))
        if self.robot_status!='ready':self.last_tick=time.monotonic();return
        if time.monotonic()-self.feedback_at>.3:
            if self.enabled:self.stop('SDK 反馈中断，已暂停')
            self.robot_status='fault';return
        if not self.enabled:
            self.command_q=self.q.copy();self.tracking_limited=False
            self.target=self.q.copy();self.grip_target=self.grip;self.last_tick=time.monotonic();return
        if self.pause_profile is not None:
            if (not self.hold_feedback_healthy()
                    or not self.hold_tracking_healthy(self.max_tracking_error)):
                self.stop('暂停保持反馈异常或跟随超限，已请求 SDK 保护模式')
                self.last_tick=time.monotonic();return
        measured=self.q.copy();measured_grip=self.grip
        grip_direction=self.grip_jog;self.grip_jog=0  # live gripper uses raw units, never simulated mm
        # Integrate from the preceding command, not from a lagging encoder sample.
        # Keep the encoder state separate so the browser always shows actual motion.
        self.q=self.command_q.copy()
        try:
            if self.policy_trajectory is None:
                super().tick()
                planned=self.q.copy()
            else:
                now=time.monotonic()
                if self.clock()-self.last_beat>LEASE:
                    raise ValueError('Policy heartbeat expired during trajectory')
                point,velocity,finished=self.policy_trajectory.sample(now)
                planned=np.radians(point)
                self.velocity=np.radians(velocity)
                self.motion=not finished
                self.last_tick=self.clock()
                if np.max(np.abs(planned-measured))>self.max_tracking_error:
                    raise ValueError('Timed trajectory tracking limit reached')
                if finished:self.policy_trajectory=None
        except ValueError as exc:
            self.stop(str(exc))
            planned=measured.copy()
        finally:
            self.q=measured;self.grip=measured_grip;self.grip_jog=grip_direction
        if not self.enabled:
            self.command_q=measured.copy();self.target=measured.copy();return
        bounded=np.clip(planned,np.maximum(LOWER,measured-self.max_tracking_error),
                        np.minimum(UPPER,measured+self.max_tracking_error))
        self.tracking_limited=bool(np.any(np.abs(planned-bounded)>1e-9))
        if self.pause_profile is not None and self.tracking_limited:
            self.stop('暂停减速轨迹触及跟随限幅，已请求 SDK 保护模式')
            return
        self.velocity[np.abs(planned-bounded)>1e-9]=0
        self.command_q=bounded.copy();planned=bounded
        opening_scale=GRIPPER_OPEN_SPEED_MULTIPLIER if self.supervised_policy else 1.
        if grip_direction:
            # Native feedback/command share motor-angle units, but slow catch controller
            # includes a 0.1 offset. Avoid inferring mm or master/follower gain of 5.
            base=self.last_grip if self.last_grip is not None else float(np.clip(self.gripper_raw+.1,0,5))
            jog_scale=opening_scale if grip_direction>0 else 1.
            self.raw_target=float(np.clip(base+grip_direction*jog_scale*.6*self.speed*.02,0,5))
        grip=None
        if self.raw_target is not None:
            previous=self.last_grip if self.last_grip is not None else float(np.clip(self.gripper_raw+.1,0,5))
            # Faster opening does not scale the final target or closing rate.
            step=.6*self.speed*.02
            grip=float(previous+np.clip(self.raw_target-previous,-step,step*opening_scale));self.last_grip=grip
        self.send({'action':'target','q':planned.tolist(),'grip':grip,'issued_at':time.monotonic()})
        if self.supervised_policy and not self.policy_gate.available(self.owner,self.enabled):
            self.policy_gate.observe(self.snapshot(),self.feedback_at)
    def snapshot(self):
        result=super().snapshot();ready=self.robot_status=='ready' and self.feedback_at>0
        result.update(simulation=False,robot_status=self.robot_status,channel=self.channel,
                      worker_running=bool(self.process and self.process.poll() is None),
                      worker_fault_reason=self.worker_fault_reason,
                      worker_protocol_version=self.worker_protocol_version,
                      policy_trajectory_protocol=PolicyTrajectory.protocol,
                      policy_tracking_limits_deg={'settle': POLICY_SETTLE_ERROR_DEG,
                          'hold': POLICY_HOLD_ERROR_DEG, 'trajectory': POLICY_TRACKING_ERROR_DEG},
                      policy_step_limits_deg={'joint': JOINT_STEP_DEG, 'norm': JOINT_STEP_NORM_DEG},
                      gripper_open_speed_multiplier=(GRIPPER_OPEN_SPEED_MULTIPLIER
                          if self.supervised_policy else 1.),
                      policy_trajectory_active=self.policy_trajectory is not None,
                      feedback_age_ms=round((time.monotonic()-self.feedback_at)*1000) if self.feedback_at else None,
                      rx_age_ms=round(self.rx_age*1000) if self.rx_age is not None else None,
                      rx_count=self.rx_count,rx_ids=self.rx_ids,currents=self.currents,error_codes=self.error_codes,
                      velocity_deg=np.degrees(self.robot_velocity).tolist(),gripper_raw=self.gripper_raw,
                      gripper_command_raw=self.last_grip,
                      policy_execution_available=bool(self.supervised_policy and self.policy_gate.available(self.owner,self.enabled)),
                      policy_execution_scope='supervised_trial' if self.supervised_policy else 'disabled',
                      policy_execution_blockers=([] if self.supervised_policy and self.policy_gate.available(self.owner,self.enabled)
                          else ['Supervised trial mode and three seconds of measured stable powered hold are required']),
                      fault_fallback_hardware_validated=False,
                      gripper_target_raw=self.raw_target,gripper_mm=None,gripper_target_mm=None,
                      model_ready=ready,command_deg=np.degrees(self.command_q).tolist() if ready else [None]*6,
                      tracking_error_deg=np.degrees(self.command_q-self.q).tolist() if ready else [None]*6,
                      tracking_limited=self.tracking_limited)
        if not ready:
            for key in ('joints_deg','pose','target_deg','target_pose'):result[key]=[None]*6
            result['points']=[];result['frames']=[]
        return result
    def close(self):
        if self.process and self.process.poll() is None:
            self.send({'action':'shutdown'})
            try:self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.note('SDK 初始化仍在执行；未强杀电机控制进程')
