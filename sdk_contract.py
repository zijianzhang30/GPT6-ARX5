"""Validated command boundary for a future live backend, tested with a fake SDK.

This module does not connect a device. Millimetres require per-device endpoint
calibration; the example master-to-follower gain of 5 is not a unit conversion.
"""
from dataclasses import dataclass
import math
import numpy as np
from control import LOWER, UPPER, vector

FOLLOWER_CONFIG = {'can_port': 'can0', 'type': 0}

@dataclass(frozen=True)
class GripperCalibration:
    closed_command: float
    open_command: float
    closed_feedback: float
    open_feedback: float
    width_mm: float = 80.

    def __post_init__(self):
        values = [self.closed_command,self.open_command,self.closed_feedback,self.open_feedback,self.width_mm]
        if not all(math.isfinite(v) for v in values) or self.width_mm <= 0:
            raise ValueError('夹爪标定参数必须为有效有限数值')
        if self.closed_command == self.open_command or self.closed_feedback == self.open_feedback:
            raise ValueError('开闭端点不能相同')

    def command(self, width_mm):
        if not math.isfinite(width_mm) or not 0 <= width_mm <= self.width_mm:
            raise ValueError('夹爪目标超出标定范围')
        return self.closed_command+(self.open_command-self.closed_command)*width_mm/self.width_mm

    def feedback(self, raw):
        if not math.isfinite(raw):
            raise ValueError('无效夹爪反馈')
        return (raw-self.closed_feedback)/(self.open_feedback-self.closed_feedback)*self.width_mm

class CommandAdapter:
    """Use only with an already initialized, supervised SDK instance.

    This is a command contract, not a live controller: no lifecycle, freshness
    timestamp or hardware emergency-stop semantics are asserted here.
    """
    def __init__(self, arm, gripper=None):
        self.arm, self.gripper = arm, gripper

    def joints(self, radians):
        q = vector(radians, 6)
        if np.any(q < LOWER) or np.any(q > UPPER):
            raise ValueError('关节目标越界')
        self.arm.set_joint_positions(positions=q.tolist())

    def grip(self, width_mm):
        if self.gripper is None:
            raise ValueError('实机夹爪需要开闭命令和反馈端点标定')
        self.arm.set_catch_pos(pos=self.gripper.command(width_mm))

    def read(self):
        values = vector(self.arm.get_joint_positions(), 7)
        return {'joint_rad':values[:6].tolist(),'gripper_raw':float(values[6]),
                'gripper_mm':self.gripper.feedback(float(values[6])) if self.gripper else None}
