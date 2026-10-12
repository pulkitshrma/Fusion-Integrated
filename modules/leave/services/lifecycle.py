"""Approved-leave cancellation, extension and resumption workflows."""
from datetime import date
from django.db import transaction
from django.utils import timezone
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import rules
from modules.leave.models import (
    LeaveApplication, LeaveBalance, LeaveLedgerEntry, LeaveLifecycleEvent,
    LeaveLifecycleRequest,
)
from modules.leave.services import workflow, applications


def _authority_for(application, resumption=False):
    steps = workflow.route_steps(application)
    if not steps:
        raise rules.PolicyViolation("workflow_route_incomplete", "No applicable authority is configured.")
    return steps[-1].assignee_user_id if resumption else steps[0].assignee_user_id


@transaction.atomic
def request_cancellation(*, application_id, actor, details=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id, status="approved"
    ).first()
    if app is None:
        raise NotFoundError("No approved leave application was found.")
    if app.start_date <= timezone.localdate():
        raise ConflictError("Pre-start cancellation is unavailable after leave has begun.", code="cancellation_window_closed")
    if app.lifecycle_requests.filter(kind="cancellation", status="pending").exists():
        raise ConflictError("A cancellation request is already pending.", code="cancellation_pending")
    request = LeaveLifecycleRequest.objects.create(
        application=app, kind="cancellation", details=details,
        current_assignee_user_id=_authority_for(app),
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status="pending",
        action="request_cancellation", actor_user_id=actor.user_id, note=details,
    )
    old = app.status
    app.status = "cancellation_pending"
    app.save(update_fields=["status", "updated_at"])
    from modules.leave.models import LeaveApplicationEvent
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="request_cancellation", actor_user_id=actor.user_id, note=details,
    )
    return request


@transaction.atomic
def request_extension(*, application_id, actor, new_end_date, details=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id, status="approved"
    ).first()
    if app is None:
        raise NotFoundError("No ongoing approved leave was found.")
    if app.category not in {"EL", "COL", "VL"}:
        raise ConflictError("Extension is supported only for EL, COL and VL.", code="extension_not_supported")
    today = timezone.localdate()
    if not (app.start_date <= today <= app.end_date):
        raise ConflictError("Extension is available only while the approved leave is ongoing.", code="extension_not_ongoing")
    if new_end_date <= app.end_date:
        raise ConflictError("The extension end date must be after the approved end date.", code="invalid_extension_period")
    incremental = applications._requested_days(app.category, app.end_date.replace(day=app.end_date.day) + __import__("datetime").timedelta(days=1), new_end_date, "")
    balance = applications._balance_for_update(app.user_id, app.category, app.start_date.year)
    if balance.available < incremental:
        raise rules.PolicyViolation("insufficient_balance", "Available balance is insufficient for the extension.")
    if app.category == "VL":
        periods = list(__import__("modules.leave.models", fromlist=["LeaveVacationPeriod"]).LeaveVacationPeriod.objects.filter(
            is_active=True, start_date__lte=app.end_date + __import__("datetime").timedelta(days=1),
            end_date__gte=new_end_date).values_list("start_date", "end_date"))
        rules.validate_vacation(app.end_date + __import__("datetime").timedelta(days=1), new_end_date, periods)
    request = LeaveLifecycleRequest.objects.create(
        application=app, kind="extension", details=details,
        requested_start_date=app.end_date + __import__("datetime").timedelta(days=1),
        requested_end_date=new_end_date,
        current_assignee_user_id=_authority_for(app),
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status="pending",
        action="request_extension", actor_user_id=actor.user_id, note=details,
    )
    return request


@transaction.atomic
def submit_resumption(*, application_id, actor, actual_resumption_date, details=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id, status="approved"
    ).first()
    if app is None:
        raise NotFoundError("No approved leave application was found.")
    if app.category not in {"EL", "COL", "VL"}:
        raise ConflictError("Resumption review is supported only for EL, COL and VL.", code="resumption_not_supported")
    if actual_resumption_date < app.start_date:
        raise ConflictError("Actual resumption date cannot precede the leave start date.", code="invalid_resumption_date")
    if app.lifecycle_requests.filter(kind="resumption", status="pending").exists():
        raise ConflictError("A resumption review is already pending.", code="resumption_pending")
    request = LeaveLifecycleRequest.objects.create(
        application=app, kind="resumption", actual_resumption_date=actual_resumption_date,
        details=details, current_assignee_user_id=_authority_for(app, resumption=True),
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status="pending",
        action="submit_resumption", actor_user_id=actor.user_id, note=details,
    )
    return request


@transaction.atomic
def decide_lifecycle(*, request_id, actor, approve, note=""):
    req = LeaveLifecycleRequest.objects.select_for_update().select_related("application").filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("No such leave lifecycle request.")
    if req.status != "pending":
        raise ConflictError("This lifecycle request is no longer pending.", code="not_actionable")
    if req.current_assignee_user_id != actor.user_id:
        raise PermissionDeniedError("Only the assigned Sanctioning Authority may process this request.")
    app = LeaveApplication.objects.select_for_update().get(pk=req.application_id)
    old = req.status
    req.status = "approved" if approve else "rejected"
    req.final_decision_by_user_id = actor.user_id
    req.final_decision_at = timezone.now()
    req.decision_note = note
    req.current_assignee_user_id = None
    req.save()
    LeaveLifecycleEvent.objects.create(
        request=req, from_status=old, to_status=req.status,
        action="approve" if approve else "reject", actor_user_id=actor.user_id, note=note,
    )
    if approve and req.kind == "cancellation":
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=app.user_id, category=app.category, year=app.start_date.year)
        balance.consumed = max(0, balance.consumed - app.requested_days)
        balance.save(update_fields=["consumed", "updated_at"])
        LeaveLedgerEntry.objects.create(
            user_id=app.user_id, application=app, category=app.category,
            amount=app.requested_days, entry_type="restore", reference=f"cancellation:{req.pk}",
        )
        app.status = "cancelled"
        app.save(update_fields=["status", "updated_at"])
    elif req.kind == "cancellation":
        app.status = "approved"
        app.save(update_fields=["status", "updated_at"])
    elif approve and req.kind == "extension":
        amount = applications._requested_days(
            app.category, req.requested_start_date, req.requested_end_date, "")
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=app.user_id, category=app.category, year=app.start_date.year)
        if balance.available < amount:
            raise rules.PolicyViolation("insufficient_balance", "Balance changed before extension approval.")
        balance.consumed += amount
        balance.save(update_fields=["consumed", "updated_at"])
        LeaveLedgerEntry.objects.create(
            user_id=app.user_id, application=app, category=app.category,
            amount=amount, entry_type="debit", reference=f"extension:{req.pk}",
        )
    elif approve and req.kind == "resumption":
        # The final authority's review is the gate. Actual-period adjustments
        # are recorded as a separate ledger adjustment; approved base dates
        # remain immutable for audit.
        delta = (req.actual_resumption_date - app.end_date).days
        if delta:
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=app.user_id, category=app.category, year=app.start_date.year)
            if delta < 0:
                restore = min(balance.consumed, app.requested_days * 0 + abs(delta))
                balance.consumed -= restore
                entry_type, amount = "restore", restore
            else:
                amount = delta
                balance.consumed += amount
                entry_type = "debit"
            balance.save(update_fields=["consumed", "updated_at"])
            LeaveLedgerEntry.objects.create(
                user_id=app.user_id, application=app, category=app.category,
                amount=amount, entry_type=entry_type, reference=f"resumption:{req.pk}",
            )
    return req
