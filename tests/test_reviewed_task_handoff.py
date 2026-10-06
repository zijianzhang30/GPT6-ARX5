import unittest

from reviewed_task_handoff import TASK_CRITERIA, result_hash, validate_reviewed_diagnostic
from test_measured_probe_diagnostic_handoff import MeasuredProbeDiagnosticHandoffTests


class ReviewedTaskHandoffTests(unittest.TestCase):
    def fixture(self):
        events=MeasuredProbeDiagnosticHandoffTests().events()
        events[0]['event']='joint_diagnostic_result'
        events[2]['command']='diagnose-empty-left-j3'
        review={'schema_version':1,'source_result_sha256':result_hash(events[0]),
                'task_criteria':dict(TASK_CRITERIA),
                'user_authorization':'可以的 继续把 启动一下这个任务 录制视频之类的 类似之前的那些操作',
                'precision_diagnostic_is_not_task_gate':True}
        return events,review

    def test_explicit_review_preserves_targets_and_diagnostic_failure(self):
        events,review=self.fixture()
        saved=validate_reviewed_diagnostic(events,'owner',review)
        self.assertEqual(saved['left']['command_deg'],events[0]['held_joints_deg'])
        self.assertFalse(events[0]['passed'])
        self.assertTrue(events[0]['motion_locked'])

    def test_faults_changed_targets_unreviewed_results_and_relaxed_criteria_rejected(self):
        for case in ('unreviewed','stale_hash','criteria','fault','uncancelled','unstable',
                     'unfinished','renew','owner','right_grip','left_target','duplicate'):
            with self.subTest(case=case):
                events,review=self.fixture()
                if case=='unreviewed':review['user_authorization']=''
                elif case=='stale_hash':review['source_result_sha256']='wrong'
                elif case=='criteria':review['task_criteria']['hold_deg']=4.
                elif case=='fault':events.insert(0,{'event':'host_quarantined'})
                elif case=='uncancelled':events[0]['failed_target_cancelled']=False
                elif case=='unstable':events[0]['stationary']=False
                elif case=='unfinished':events.pop()
                elif case=='renew':events[-3]['command']='renew'
                elif case=='owner':events[-2]['state']['arms']['left']['raw_state']['owner']='other'
                elif case=='right_grip':events[-2]['state']['arms']['right']['raw_state']['gripper_command_raw']+=.2
                elif case=='left_target':events[-2]['state']['arms']['left']['raw_state']['command_deg'][2]+=1
                elif case=='duplicate':events.insert(0,events[0])
                with self.assertRaises(ValueError):validate_reviewed_diagnostic(events,'owner',review)
