"""Pure ELM policy rules. No Django imports."""
from datetime import date, timedelta
from decimal import Decimal

CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})
ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8"), "RH": Decimal("2"), "SCL": Decimal("15"),
    "EL": Decimal("30"), "COL": Decimal("20"), "VL": Decimal("60"),
}
CARRY_FORWARD = frozenset({"EL", "COL"})


class PolicyViolation(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate_category(category, employee_kind):
    if category not in CATEGORIES:
        raise PolicyViolation("unsupported_category", "Only CL, RH, SCL, EL, COL and VL are supported.")
    if category == "VL" and employee_kind != "faculty":
        raise PolicyViolation("category_not_applicable", "VL is applicable only to faculty.")
    if category == "EL" and employee_kind == "faculty":
        raise PolicyViolation("category_not_applicable", "This baseline grants EL directly to non-faculty employees.")


def validate_rh(start, end, published_rh_dates):
    if start != end or start not in set(published_rh_dates):
        raise PolicyViolation("rh_calendar_mismatch", "RH must match an effective published Restricted Holiday.")


def validate_vacation(start, end, vacation_periods):
    if not any(start >= a and end <= b for a, b in vacation_periods):
        raise PolicyViolation("outside_vacation", "VL may be availed only within an Academic Calendar vacation period.")


def validate_overlap(start, end, existing, *, half_day=None, category=None):
    for item in existing:
        if start <= item["end"] and end >= item["start"]:
            distinct_halves = (
                category == item.get("category") == "CL"
                and start == end == item["start"] == item["end"]
                and half_day and item.get("half_day")
                and half_day != item.get("half_day")
            )
            if not distinct_halves:
                raise PolicyViolation("leave_overlap", "The requested period overlaps pending or approved leave.")


def year_end_outcome(category, unused):
    unused = Decimal(str(unused))
    if category == "VL":
        return {"carry": Decimal("0"), "credit_el": unused / Decimal("2"), "lapse": Decimal("0")}
    if category in {"CL", "RH", "SCL"}:
        return {"carry": Decimal("0"), "credit_el": Decimal("0"), "lapse": unused}
    if category in {"EL", "COL"}:
        return {"carry": unused, "credit_el": Decimal("0"), "lapse": Decimal("0")}
    raise PolicyViolation("unsupported_category", "Unsupported leave category.")
