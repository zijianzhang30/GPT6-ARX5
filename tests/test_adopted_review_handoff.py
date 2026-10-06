import copy
import unittest

from adopted_review_handoff import validate_adopted_initial_log
from tests.test_initial_review_handoff import InitialReviewTests


class AdoptedInitialLogTests(unittest.TestCase):
    def events(self):
        old = InitialReviewTests().events()
        old[-3].update(retain_settle_fault_hold=False, one_empty_left_probe=False,
                       one_empty_left_joint_diagnostic=False)
        return [dict(event='powered_hold_adopted', adopted=True, released_hold=False,
                     joint_commands_deg={'left':[0.] * 6}), old[1], *old[-3:]]

    def check(self, events):
        return validate_adopted_initial_log(events, 'owner', 'left', 'right')

    def test_accepts_exact_completed_adoption_without_inputs(self):
        self.assertEqual(set(self.check(self.events())), {'left', 'right'})

    def test_rejects_any_input_fault_extra_adoption_or_incomplete_start(self):
        for kind in ('request', 'result', 'rejected', 'host_error', 'camera_gate',
                     'review_command_started', 'review_command_finished',
                     'powered_hold_adopted', 'observation'):
            for position in range(6):
                e=self.events(); e.insert(position, {'event':kind})
                with self.subTest(kind=kind, position=position), self.assertRaises(ValueError):
                    self.check(e)
        for index in range(5):
            e=self.events(); del e[index]
            with self.subTest(missing=index), self.assertRaises(ValueError):
                self.check(e)

    def test_rejects_wrong_preparation_arm_changed_targets_and_unhealthy_hold(self):
        for mutate in (
            lambda e:e[0].update(released_hold=True),
            lambda e:e[1].update(arm='left'),
            lambda e:e[-3].update(one_arm_at_a_time=False),
            lambda e:e[-3].update(retain_settle_fault_hold=True),
            lambda e:e[-1].update(arm='left'),
            lambda e:e[0].update(joint_commands_deg={'left':[1.] * 6}),
        ):
            e=self.events(); mutate(e)
            with self.assertRaises(ValueError):self.check(e)
        for side in ('left','right'):
            for key,value in [('owner','other'),('moving',True),('enabled',False),
                              ('worker_fault_reason','fault'),('error_codes',[1]),
                              ('command_deg',[float('nan')] * 6)]:
                e=self.events(); e[-2]['state']['arms'][side]['raw_state'][key]=value
                with self.subTest(side=side,key=key), self.assertRaises(ValueError):self.check(e)


if __name__ == '__main__':
    unittest.main()
