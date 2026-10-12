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


def list_pending_attendance_syncs(limit: int = 100) -> list[dict]:
    """Public polling contract for the attendance service's outbox consumer."""
    from modules.leave.models import LeaveAttendanceSyncOutbox
    return list(LeaveAttendanceSyncOutbox.objects.filter(status="pending")
                .order_by("created_at", "id").values(
                    "id", "user_id", "payload", "created_at"
                )[:max(1, min(limit, 500))])


@transaction.atomic
def mark_attendance_sync_result(outbox_id: int, *, success: bool, details: str = "") -> bool:
    """Acknowledge a delivered attendance update; failed deliveries remain retryable."""
    from django.utils import timezone
    from modules.leave.models import LeaveAttendanceSyncOutbox
    item = LeaveAttendanceSyncOutbox.objects.select_for_update().filter(pk=outbox_id).first()
    if item is None or item.status == "processed":
        return False
    item.attempts += 1
    item.status = "processed" if success else "failed"
    item.last_error = "" if success else details
    item.processed_at = timezone.now() if success else None
    item.save(update_fields=["attempts", "status", "last_error", "processed_at"])
    return True


@transaction.atomic
def retry_attendance_sync(outbox_id: int) -> bool:
    from modules.leave.models import LeaveAttendanceSyncOutbox
    item = LeaveAttendanceSyncOutbox.objects.select_for_update().filter(
        pk=outbox_id, status="failed"
    ).first()
    if item is None:
        return False
    item.status = "pending"
    item.last_error = ""
    item.save(update_fields=["status", "last_error"])
    return True
