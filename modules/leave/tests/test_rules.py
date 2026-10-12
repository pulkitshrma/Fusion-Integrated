from datetime import date
from decimal import Decimal
from django.test import SimpleTestCase
from modules.leave.domain import rules


class LeavePolicyRulesTests(SimpleTestCase):
    def test_only_faculty_can_use_vacation_leave(self):
        rules.validate_category("VL", "faculty")
        with self.assertRaises(rules.PolicyViolation):
            rules.validate_category("VL", "staff")

    def test_faculty_el_is_available_only_through_a_credited_balance(self):
        # Applicability is balance-controlled: faculty receive no direct EL
        # entitlement, but may use EL converted from unused VL.
        rules.validate_category("EL", "faculty")

    def test_restricted_holiday_must_be_one_published_date(self):
        holiday = date(2026, 10, 2)
        rules.validate_rh(holiday, holiday, {holiday})
        with self.assertRaises(rules.PolicyViolation):
            rules.validate_rh(holiday, date(2026, 10, 3), {holiday})

    def test_vacation_must_be_inside_one_academic_calendar_period(self):
        period = (date(2026, 5, 1), date(2026, 6, 30))
        rules.validate_vacation(date(2026, 5, 4), date(2026, 5, 20), [period])
        with self.assertRaises(rules.PolicyViolation):
            rules.validate_vacation(date(2026, 4, 30), date(2026, 5, 20), [period])

    def test_half_day_cl_same_date_different_half_is_non_overlapping(self):
        existing = [{"start": date(2026, 10, 12), "end": date(2026, 10, 12),
                     "category": "CL", "half_day": "first_half"}]
        rules.validate_overlap(date(2026, 10, 12), date(2026, 10, 12),
                               existing, category="CL", half_day="second_half")
        with self.assertRaises(rules.PolicyViolation):
            rules.validate_overlap(date(2026, 10, 12), date(2026, 10, 12),
                                   existing, category="CL", half_day="first_half")

    def test_year_end_carry_forward_and_vl_conversion(self):
        self.assertEqual(rules.year_end_outcome("CL", 3)["lapse"], Decimal("3"))
        self.assertEqual(rules.year_end_outcome("EL", 4)["carry"], Decimal("4"))
        self.assertEqual(rules.year_end_outcome("COL", 2)["carry"], Decimal("2"))
        self.assertEqual(rules.year_end_outcome("VL", 5)["credit_el"], Decimal("2.5"))
        self.assertEqual(rules.year_end_outcome("VL", 5)["carry"], Decimal("0"))
