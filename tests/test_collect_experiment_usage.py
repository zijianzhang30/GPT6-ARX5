import json
from pathlib import Path
import tempfile
import unittest

from tools.collect_experiment_usage import collect


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.start = '2026-10-17T08:00:00Z'
        self.end = '2026-10-17T08:01:00Z'

    def log(self, name, events):
        path = self.root / name
        path.write_text(''.join(json.dumps(e)+'\n' for e in events))
        return path

    def response(self, ident='r1', **overrides):
        usage = dict(input_tokens=100, cached_input_tokens=80, cache_write_input_tokens=5,
                     output_tokens=20, reasoning_output_tokens=7, total_tokens=120)
        usage.update(overrides)
        return dict(timestamp=self.start, type='token_usage_record',
                    payload=dict(response_id=ident, usage=usage))

    def test_dedup_boundaries_and_overlapping_categories(self):
        response = self.response()
        call = dict(timestamp='2026-10-17T16:00:30+08:00', type='response_item',
                    payload=dict(type='function_call', call_id='c1', name='functions.exec',
                                 arguments='PRIVATE TOOL BODY'))
        outside = dict(self.response('outside'), timestamp='2026-10-17T07:59:59Z')
        snapshot = dict(timestamp=self.end, type='event_msg',
                        payload=dict(type='token_count', info={'total_token_usage': {'total_tokens': 999999}}))
        p = self.log('session.jsonl', [response, response, call, call, outside, snapshot])
        result, rows, calls = collect([p], self.start, self.end)
        self.assertEqual(result['unique_model_response_records'], 1)
        self.assertEqual(result['top_level_tool_calls'], 1)
        self.assertEqual(result['token_totals']['total_tokens'], 120)
        self.assertEqual(result['token_totals']['uncached_input_tokens'], 20)
        self.assertEqual(result['token_totals']['ordinary_input_tokens'], 15)
        self.assertIsNone(result['nested_tool_calls'])
        self.assertNotIn('PRIVATE', json.dumps([result, rows, calls]))

    def test_multiple_logs_and_conflicting_duplicates(self):
        a = self.log('a.jsonl', [self.response()])
        b = self.log('b.jsonl', [self.response(), self.response('r2')])
        result, _, _ = collect([a, b], self.start, self.end)
        self.assertEqual(result['unique_model_response_records'], 2)
        b = self.log('b.jsonl', [self.response(output_tokens=21, total_tokens=121)])
        with self.assertRaisesRegex(ValueError, 'Conflicting duplicate'):
            collect([a, b], self.start, self.end)

    def test_missing_metadata_is_unknown_not_zero(self):
        p = self.log('session.jsonl', [])
        result, _, _ = collect([p], self.start, self.end)
        self.assertIsNone(result['token_totals']['total_tokens'])
        self.assertIsNone(result['robot'])
        event = self.response()
        event['payload']['usage'] = {'input_tokens': 100, 'output_tokens': 20}
        p = self.log('session.jsonl', [event])
        result, _, _ = collect([p], self.start, self.end)
        self.assertEqual(result['token_totals']['total_tokens'], 120)
        self.assertIsNone(result['token_totals']['cached_input_tokens'])

    def test_robot_requests_include_rejections_and_explicit_cleanup_boundary(self):
        events = [
            dict(timestamp=self.start, event='request', tool='move_to'),
            dict(timestamp=self.start, event='review_command_finished', command='tool_json',
                 outcome='rejected', command_wall_s=0.1),
            dict(timestamp=self.end, event='request', tool='move_to'),
            dict(timestamp=self.end, event='review_command_finished', command='tool_json',
                 outcome='completed', command_wall_s=1.2),
            dict(timestamp=self.end, event='gripper_preparation_target'),
        ]
        p = self.log('session.jsonl', [])
        r = self.log('robot.jsonl', events)
        result, _, _ = collect([p], self.start, self.end, r, '2026-10-17T08:00:30Z')
        robot = result['robot']
        self.assertEqual(robot['json_requests'], 2)
        self.assertEqual(robot['task_json_requests'], 1)
        self.assertEqual(robot['after_task_json_requests'], 1)
        self.assertEqual(robot['host_outcomes'], {'rejected': 1, 'completed': 1})
        self.assertEqual(robot['empty_gripper_internal_targets'], 1)

    def test_timezone_required_and_invalid_window_rejected(self):
        with self.assertRaises(ValueError):
            collect([], '2026-10-17T08:00:00', self.end)
        with self.assertRaises(ValueError):
            collect([], self.end, self.start)

    def test_nested_usage_and_invalid_line_diagnostics(self):
        event = self.response()
        event['payload']['usage'] = dict(input_tokens=100, output_tokens=20,
            input_tokens_details=dict(cached_tokens=80, cache_write_tokens=5),
            output_tokens_details=dict(reasoning_tokens=7))
        p = self.log('session.jsonl', [event])
        with p.open('a') as f:
            f.write('{truncated line\n')
        result, _, _ = collect([p], self.start, self.end)
        self.assertEqual(result['token_totals']['cached_input_tokens'], 80)
        self.assertEqual(result['token_totals']['reasoning_output_tokens'], 7)
        self.assertEqual(result['diagnostics']['session_invalid_json_lines'], 1)


if __name__ == '__main__':
    unittest.main()
