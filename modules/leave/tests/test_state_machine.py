from django.test import SimpleTestCase
from modules.leave.domain import state_machine as sm


class LeaveStateMachineTests(SimpleTestCase):
    def test_substitute_acceptance_routes_to_unit_head(self):
        self.assertEqual(sm.transition(sm.AWAITING_SUBSTITUTE, "substitute_accept"),
                         sm.AWAITING_UNIT_HEAD)

    def test_declined_substitute_requires_applicant_action(self):
        self.assertEqual(sm.transition(sm.AWAITING_SUBSTITUTE, "substitute_decline"),
                         sm.APPLICANT_ACTION_REQUIRED)

    def test_withdrawal_is_only_for_pending_request(self):
        self.assertEqual(sm.transition(sm.AWAITING_UNIT_HEAD, "withdraw"), sm.WITHDRAWN)
        with self.assertRaises(ValueError):
            sm.transition(sm.APPROVED, "withdraw")
