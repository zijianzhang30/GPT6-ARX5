import copy
import unittest

from measured_probe_diagnostic_handoff import validate_failed_probe_for_diagnosis
from test_initial_review_handoff import InitialReviewTests


class MeasuredProbeDiagnosticHandoffTests(unittest.TestCase):
    def events(self):
        observation = InitialReviewTests().events()[-2]
        observation['state']['arms']['left']['raw_state']['gripper_command_raw'] = 4.8
        return [dict(event='empty_probe_result', passed=False, stationary=True,
                     motion_locked=True, failed_target_cancelled=True, control_state='holding',
                     held_joints_deg=observation['state']['arms']['left']['raw_state']['command_deg']),
                copy.deepcopy(observation),
                dict(event='review_command_finished',command='probe-empty-up-3mm',outcome='completed'),
                dict(event='review_command_started',command='observe',command_index=9),
                copy.deepcopy(observation),
                dict(event='review_command_finished',command='observe',command_index=9,outcome='completed')]

    def test_cancelled_stationary_failed_probe_and_unchanged_hold_only(self):
        saved = validate_failed_probe_for_diagnosis(self.events(),'owner')
        self.assertEqual(saved['left']['gripper_command_raw'],4.8)

    def test_diagnostic_result_cannot_become_an_ordinary_healthy_probe_source(self):
        from healthy_probe_handoff import validate_healthy_probe_source
        from test_healthy_probe_handoff import HealthyProbeHandoffTests
        events=HealthyProbeHandoffTests().events()
        events.insert(0,{'event':'joint_diagnostic_result','passed':True})
        with self.assertRaises(ValueError): validate_healthy_probe_source(events,'owner')

    def test_rejects_faults_pending_work_motion_changes_and_repeated_diagnosis(self):
        for case in ('passed','unstable','not_cancelled','unlocked','wrong_outcome',
                     'wrong_command','changed_target','changed_grip','wrong_owner',
                     'fault','repeat','unfinished','duplicate_result'):
            with self.subTest(case=case):
                events=self.events()
                if case=='passed': events[0]['passed']=True
                elif case=='unstable': events[0]['stationary']=False
                elif case=='not_cancelled': events[0]['failed_target_cancelled']=False
                elif case=='unlocked': events[0]['motion_locked']=False
                elif case=='wrong_outcome': events[-1]['outcome']='failed'
                elif case=='wrong_command': events[-3]['command']='renew'
                elif case=='changed_target': events[-2]['state']['arms']['left']['raw_state']['command_deg'][2] += 1
                elif case=='changed_grip': events[-2]['state']['arms']['right']['raw_state']['gripper_command_raw'] += .2
                elif case=='wrong_owner': events[-2]['state']['arms']['left']['raw_state']['owner']='other'
                elif case=='fault': events.insert(0,{'event':'host_quarantined'})
                elif case=='repeat': events.insert(0,{'event':'joint_diagnostic_result'})
                elif case=='unfinished': events.pop()
                elif case=='duplicate_result': events.insert(0,events[0])
                with self.assertRaises(ValueError): validate_failed_probe_for_diagnosis(events,'owner')
