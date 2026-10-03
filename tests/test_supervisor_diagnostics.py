import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from r5_policy_backend import R5ExecutionFault
from r5_policy_supervisor import R5PolicySupervisor


def test_diagnostics_preserve_original_stall_abort():
    robot = Mock(busy=False)
    robot.client = SimpleNamespace(arm='left')
    robot.abort.side_effect = R5ExecutionFault('protective stop')
    supervisor = R5PolicySupervisor(robot)
    supervisor.thread = threading.current_thread()
    supervisor.last_check = time.monotonic() - .31
    with pytest.raises(R5ExecutionFault, match='protective stop'):
        supervisor.check()
    robot.abort.assert_called_once()
    assert 'limit_s=0.3' in robot.abort.call_args.args[0]
    assert supervisor.diagnostics()['stall']['arm'] == 'left'
    assert supervisor.diagnostics()['stall']['worker_stack']
    robot.vision_check.assert_not_called()


def test_failed_check_does_not_refresh_last_success():
    robot = Mock()
    supervisor = R5PolicySupervisor(robot)
    supervisor._check_robot()
    last = supervisor.last_check
    assert supervisor.check_started_at is None
    robot.check.side_effect = R5ExecutionFault('read failed')
    with pytest.raises(R5ExecutionFault):
        supervisor._check_robot()
    assert supervisor.last_check == last
    assert supervisor.check_started_at is not None
    assert len(supervisor.diagnostics()['recent_checks']) == 1
