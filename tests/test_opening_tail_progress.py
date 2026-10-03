"""Offline regression for flower trial03's final opening increment."""
from unittest.mock import Mock

import pytest

from supervised_policy import open_empty_gripper
from test_gripper_check import Client
from test_r5_policy_backend import Clock


START_COMMAND = 2.288014354705811
START_FEEDBACK = 2.1953916549682617
# Last stable feedback for each submitted target in the recorded failure.
RECORDED_ENDPOINTS = [2.686732292175293, 3.1883726119995117,
                      3.690011978149414, 4.190507888793945,
                      4.690240859985352, 4.692150115966797]


class OpeningClient(Client):
    def __init__(self, endpoints, *, start=START_COMMAND, measured=START_FEEDBACK):
        super().__init__()
        self.current.update(enabled=True, owner=self.client, control_state='holding',
                            speed=.3, gripper_command_raw=start,
                            gripper_target_raw=start, gripper_raw=measured,
                            gripper_open_speed_multiplier=5.)
        self.endpoints = iter(endpoints)
        self.targets = []

    def command(self, action, **fields):
        super().command(action, **fields)
        if action == 'target':
            self.targets.append(fields['gripper_raw'])
            self.current['gripper_raw'] = next(self.endpoints)
        return self.state()


def run_open(client, *, target=4.8, cameras=None):
    clock = Clock()
    log = Mock()
    result = open_empty_gripper(client, cameras or Mock(), target, log,
                                clock=clock, sleep=clock.sleep)
    return result, log


def test_recorded_final_increment_reaches_hold_without_extra_targets():
    client = OpeningClient(RECORDED_ENDPOINTS)
    result, log = run_open(client)
    assert result['control_state'] == 'holding'
    assert result['gripper_command_raw'] == 4.8
    assert result['gripper_raw'] == RECORDED_ENDPOINTS[-1]
    assert client.targets == pytest.approx([START_COMMAND + .5*i for i in range(1, 6)] + [4.8])
    assert [n for n, _ in client.commands].count('pause_hold') == 1
    assert not any(n in ('enable', 'stop', 'settings') for n, _ in client.commands)


def test_final_increment_outside_absolute_tolerance_still_times_out():
    # The preceding full step is inside its own tolerance; the final target isn't.
    client = OpeningClient(RECORDED_ENDPOINTS[:4] + [4.644, 4.644])
    with pytest.raises(TimeoutError, match='Opening step stalled'):
        run_open(client)
    assert len(client.targets) == 6  # No retries or force increase.
    assert not any(n == 'pause_hold' for n, _ in client.commands)


def test_a_full_final_step_cannot_borrow_previous_progress():
    # All full steps still need their own progress, even inside the endpoint band.
    client = OpeningClient([4.74, 4.74], start=4.6, measured=4.6)
    client.current['gripper_open_speed_multiplier'] = 1.
    with pytest.raises(TimeoutError, match='Opening step stalled'):
        run_open(client)
    assert len(client.targets) == 2


def test_single_small_request_cannot_borrow_nonexistent_progress():
    client = OpeningClient([4.692], start=4.788014354705811, measured=4.69024)
    with pytest.raises(TimeoutError, match='Opening step stalled'):
        run_open(client)
    assert len(client.targets) == 1


@pytest.mark.parametrize('fault', ['unstable', 'unacknowledged', 'owner', 'joint_drift', 'camera'])
def test_final_increment_retains_other_checks(fault):
    client = OpeningClient(RECORDED_ENDPOINTS)
    original = client.command
    count = 0

    def command(action, **fields):
        nonlocal count
        original(action, **fields)
        if len(client.targets) == 6:
            if fault == 'unstable' and action == 'heartbeat':
                count += 1
                client.current['gripper_raw'] = 4.69 + .03*(count % 2)
            elif fault == 'unacknowledged':
                client.current['gripper_command_raw'] = client.targets[-2]
            elif fault == 'owner':
                client.current['owner'] = 'other-controller'
            elif fault == 'joint_drift':
                client.current['joints_deg'][0] += 2.
        return client.state()

    client.command = command
    cameras = Mock()
    if fault == 'camera':
        def check():
            if len(client.targets) == 6:
                raise ValueError('camera stale')
        cameras.check.side_effect = check
    with pytest.raises((TimeoutError, ValueError)):
        run_open(client, cameras=cameras)
    assert len(client.targets) == 6
    assert not any(n == 'pause_hold' for n, _ in client.commands)
