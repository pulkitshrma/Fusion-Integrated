"""Public integration contract for the external Academic Calendar module."""
from dataclasses import dataclass
from datetime import date
from collections.abc import Iterable
from django.db import transaction
from modules.leave.models import LeaveVacationPeriod


@dataclass(frozen=True)
class VacationPeriodDTO:
    external_id: str
    name: str
    start_date: date
    end_date: date
    academic_year: str


@transaction.atomic
def sync_vacation_periods(periods: Iterable[VacationPeriodDTO]) -> int:
    """Replace synchronized vacation windows for the academic years supplied.

    The Academic Calendar remains the source of truth. Empty input is a no-op;
    an invalid batch is rejected before any active period is changed.
    """
    rows = list(periods)
    if not rows:
        return 0
    for row in rows:
        if not row.external_id or not row.academic_year or row.end_date < row.start_date:
            raise ValueError("Every vacation period needs an external id, academic year and valid date range.")
    years = {row.academic_year for row in rows}
    LeaveVacationPeriod.objects.filter(academic_year__in=years).update(is_active=False)
    for row in rows:
        LeaveVacationPeriod.objects.update_or_create(
            external_id=row.external_id,
            defaults={
                "name": row.name, "start_date": row.start_date,
                "end_date": row.end_date, "academic_year": row.academic_year,
                "is_active": True,
            },
        )
    return len(rows)


def list_vacation_periods(start: date, end: date) -> list[VacationPeriodDTO]:
    return [
        VacationPeriodDTO(external_id=row.external_id, name=row.name,
                          start_date=row.start_date, end_date=row.end_date,
                          academic_year=row.academic_year)
        for row in LeaveVacationPeriod.objects.filter(
            is_active=True, start_date__lte=end, end_date__gte=start
        ).order_by("start_date")
    ]
