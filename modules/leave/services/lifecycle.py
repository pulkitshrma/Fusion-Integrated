"""Approved-leave cancellation, extension and resumption workflows."""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import rules
from modules.leave.models import (
    LeaveApplication, LeaveApplicationEvent, LeaveAttendanceSyncOutbox, LeaveBalance, LeaveLedgerEntry,
    LeaveLifecycleEvent, LeaveLifecycleRequest, LeaveVacationPeriod,
)
from modules.leave.services import applications, workflow, notifications


def _effective_approved_end(application):
    extension_end = application.lifecycle_requests.filter(
        kind="extension", status="approved", requested_end_date__isnull=False
    ).order_by("-requested_end_date").values_list("requested_end_date", flat=True).first()
    return max(application.end_date, extension_end) if extension_end else application.end_date


def _first_route_step(application):
    return workflow.route_steps(application)[0]


def _last_route_step(application):
    return workflow.route_steps(application)[-1]


@transaction.atomic
def request_cancellation(*, application_id, actor, details=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id, status="approved"
    ).first()
    if app is None:
        raise NotFoundError("No approved leave application was found.")
    if app.start_date <= timezone.localdate():
        raise ConflictError("Pre-start cancellation is unavailable after leave has begun.", code="cancellation_window_closed")
    if app.lifecycle_requests.filter(kind="cancellation", status__in=["pending", "awaiting_substitute", "applicant_action_required"]).exists():
        raise ConflictError("A cancellation request is already pending.", code="cancellation_pending")
    step = _first_route_step(app)
    request = LeaveLifecycleRequest.objects.create(
        application=app, kind="cancellation", details=details,
        current_assignee_user_id=step.assignee_user_id,
        current_step_type=step.step_type,
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status="pending",
        action="request_cancellation", actor_user_id=actor.user_id, note=details,
    )
    notifications.notify_lifecycle_assignee(request)
    old = app.status
    app.status = "cancellation_pending"
    app.save(update_fields=["status", "updated_at"])
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="request_cancellation", actor_user_id=actor.user_id, note=details,
    )
    return request


@transaction.atomic
def request_extension(*, application_id, actor, new_end_date, details="", substitute_user_id=None, supporting_evidence_reference=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id, status="approved"
    ).first()
    if app is None:
        raise NotFoundError("No ongoing approved leave was found.")
    if app.category not in {"EL", "COL", "VL"}:
        raise ConflictError("Extension is supported only for EL, COL and VL.", code="extension_not_supported")
    if app.actual_end_date or app.lifecycle_requests.filter(kind="resumption", status="approved").exists():
        raise ConflictError("An extension cannot be requested after resumption has been approved.", code="resumption_already_approved")
    if app.lifecycle_requests.filter(kind="resumption", status="pending").exists():
        raise ConflictError("A resumption review is already pending.", code="resumption_pending")
    applications._validate_evidence(app.category, supporting_evidence_reference)
    today = timezone.localdate()
    effective_end = _effective_approved_end(app)
    if not (app.start_date <= today <= effective_end):
        raise ConflictError("Extension is available only while the approved leave is ongoing.", code="extension_not_ongoing")
    if new_end_date <= effective_end:
        raise ConflictError("The extension end date must be after the approved end date.", code="invalid_extension_period")
    increment_start = effective_end + timedelta(days=1)
    incremental = applications._requested_days(app.category, increment_start, new_end_date, "")
    applications._validate_overlap(app.user_id, increment_start, new_end_date, app.category, "")
    balance = applications._balance_for_update(app.user_id, app.category, app.start_date.year, app.employee_kind)
    if balance.available < incremental:
        raise rules.PolicyViolation("insufficient_balance", "Available balance is insufficient for the extension.")
    if app.category == "VL":
        periods = list(LeaveVacationPeriod.objects.filter(
            is_active=True, start_date__lte=increment_start,
            end_date__gte=new_end_date,
        ).values_list("start_date", "end_date"))
        rules.validate_vacation(increment_start, new_end_date, periods)
    if substitute_user_id:
        applications._validate_substitute(
            applicant_id=app.user_id, substitute_id=substitute_user_id,
            start=increment_start, end=new_end_date,
        )
        request_status = "awaiting_substitute"
        assignee = substitute_user_id
        step_type = "substitute"
    else:
        step = _first_route_step(app)
        request_status = "pending"
        assignee = step.assignee_user_id
        step_type = step.step_type
    request = LeaveLifecycleRequest.objects.create(
        application=app, kind="extension", status=request_status, details=details,
        supporting_evidence_reference=supporting_evidence_reference,
        requested_start_date=increment_start, requested_end_date=new_end_date,
        substitute_user_id=substitute_user_id,
        current_assignee_user_id=assignee, current_step_type=step_type,
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status=request_status,
        action="request_extension", actor_user_id=actor.user_id, note=details,
    )
    notifications.notify_lifecycle_assignee(request)
    return request


@transaction.atomic
def respond_extension_substitute(*, request_id, actor, accept, note=""):
    req = LeaveLifecycleRequest.objects.select_for_update().select_related("application").filter(
        pk=request_id, kind="extension", status="awaiting_substitute",
        substitute_user_id=actor.user_id,
    ).first()
    if req is None:
        raise NotFoundError("No extension substitute request is assigned to you.")
    old = req.status
    if accept:
        applications._validate_substitute(
            applicant_id=req.application.user_id, substitute_id=actor.user_id,
            start=req.requested_start_date, end=req.requested_end_date,
        )
        step = _first_route_step(req.application)
        req.status = "pending"
        req.current_assignee_user_id = step.assignee_user_id
        req.current_step_type = step.step_type
    else:
        req.status = "applicant_action_required"
        req.current_assignee_user_id = req.application.user_id
        req.current_step_type = "applicant"
    req.substitute_response = "accepted" if accept else "declined"
    req.decision_note = note
    req.save()
    LeaveLifecycleEvent.objects.create(
        request=req, from_status=old, to_status=req.status,
        action="substitute_accept" if accept else "substitute_decline",
        actor_user_id=actor.user_id, note=note,
    )
    notifications.notify_lifecycle_assignee(req)
    return req


@transaction.atomic
def nominate_extension_replacement(*, request_id, actor, substitute_user_id):
    req = LeaveLifecycleRequest.objects.select_for_update().select_related("application").filter(
        pk=request_id, kind="extension", status="applicant_action_required",
        application__user_id=actor.user_id,
    ).first()
    if req is None:
        raise NotFoundError("No extension request requires a replacement substitute.")
    applications._validate_substitute(
        applicant_id=req.application.user_id, substitute_id=substitute_user_id,
        start=req.requested_start_date, end=req.requested_end_date,
    )
    old = req.status
    req.substitute_user_id = substitute_user_id
    req.substitute_response = ""
    req.status = "awaiting_substitute"
    req.current_assignee_user_id = substitute_user_id
    req.current_step_type = "substitute"
    req.save()
    LeaveLifecycleEvent.objects.create(
        request=req, from_status=old, to_status=req.status,
        action="nominate_replacement", actor_user_id=actor.user_id,
    )
    notifications.notify_lifecycle_assignee(req)
    return req


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
    if actual_resumption_date > timezone.localdate():
        raise ConflictError("Resumption can be submitted only after the employee has returned to duty.", code="future_resumption_date")
    if app.lifecycle_requests.filter(kind="extension", status__in=["pending", "awaiting_substitute", "applicant_action_required"]).exists():
        raise ConflictError("Resolve the pending extension request before submitting resumption.", code="extension_pending")
    if app.lifecycle_requests.filter(kind="resumption", status__in=["pending", "approved"]).exists():
        raise ConflictError("A resumption review is already pending.", code="resumption_pending")
    step = _last_route_step(app)
    req = LeaveLifecycleRequest.objects.create(
        application=app, kind="resumption", actual_resumption_date=actual_resumption_date,
        details=details, current_assignee_user_id=step.assignee_user_id,
        current_step_type=step.step_type,
    )
    LeaveLifecycleEvent.objects.create(
        request=req, from_status="", to_status="pending",
        action="submit_resumption", actor_user_id=actor.user_id, note=details,
    )
    notifications.notify_lifecycle_assignee(req)
    return req


@transaction.atomic
def decide_lifecycle(*, request_id, actor, approve, note=""):
    req = LeaveLifecycleRequest.objects.select_for_update().select_related("application").filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("No such leave lifecycle request.")
    if req.status != "pending":
        raise ConflictError("This lifecycle request is no longer pending.", code="not_actionable")
    if req.current_assignee_user_id != actor.user_id:
        raise PermissionDeniedError("Only the currently assigned workflow actor may process this request.")
    app = LeaveApplication.objects.select_for_update().get(pk=req.application_id)
    if req.kind == "resumption":
        required_permission = "employee_leave_management.workflow.sanction"
    elif req.current_step_type == "unit_head":
        required_permission = "employee_leave_management.workflow.review"
    else:
        required_permission = "employee_leave_management.workflow.sanction"
    if not actor.has_permission(required_permission):
        raise PermissionDeniedError(f"This action requires {required_permission}.")
    old = req.status
    final = req.kind == "resumption" or req.current_step_type == "sanction" or (
        req.current_step_type == "unit_head" and app.category in {"CL", "RH"}
    )
    if not final:
        if req.current_step_type == "establishment" and not approve:
            raise ConflictError("Establishment processing must route the request onward.", code="invalid_establishment_action")
        steps = workflow.route_steps(app)
        current_index = next((i for i, s in enumerate(steps)
                              if s.assignee_user_id == actor.user_id
                              and s.step_type == req.current_step_type), None)
        if current_index is None or current_index + 1 >= len(steps):
            raise ConflictError("The configured workflow route has no next authority.", code="workflow_route_incomplete")
        next_step = steps[current_index + 1]
        req.current_assignee_user_id = next_step.assignee_user_id
        req.current_step_type = next_step.step_type
        req.decision_note = note or ("Recommended" if approve else "Not Recommended")
        req.save(update_fields=["current_assignee_user_id", "current_step_type", "decision_note", "updated_at"])
        LeaveLifecycleEvent.objects.create(
            request=req, from_status=old, to_status="pending",
            action=("route" if req.current_step_type == "establishment" else
                    "recommended" if approve else "not_recommended"),
            actor_user_id=actor.user_id, note=note,
        )
        notifications.notify_lifecycle_assignee(req)
        return req

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
    if req.kind == "cancellation":
        if approve:
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=app.user_id, category=app.category, year=app.start_date.year)
            balance.consumed = max(Decimal("0"), balance.consumed - app.requested_days)
            balance.save(update_fields=["consumed", "updated_at"])
            LeaveLedgerEntry.objects.create(
                user_id=app.user_id, application=app, category=app.category,
                amount=app.requested_days, entry_type="restore", reference=f"cancellation:{req.pk}",
            )
            app.status = "cancelled"
        else:
            app.status = "approved"
        app.save(update_fields=["status", "updated_at"])
    elif approve and req.kind == "extension":
        amount = applications._requested_days(app.category, req.requested_start_date, req.requested_end_date, "")
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
        effective_end = _effective_approved_end(app)
        delta = (req.actual_resumption_date - effective_end).days
        if delta:
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=app.user_id, category=app.category, year=app.start_date.year)
            amount = Decimal(abs(delta))
            if delta < 0:
                extension_days = LeaveLedgerEntry.objects.filter(
                    application=app, reference__startswith="extension:"
                ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
                amount = min(balance.consumed, app.requested_days + extension_days, amount)
                balance.consumed -= amount
                entry_type = "restore"
            else:
                balance.consumed += amount
                entry_type = "debit"
            balance.save(update_fields=["consumed", "updated_at"])
            LeaveLedgerEntry.objects.create(
                user_id=app.user_id, application=app, category=app.category,
                amount=amount, entry_type=entry_type, reference=f"resumption:{req.pk}",
            )
        app.actual_end_date = req.actual_resumption_date
        app.save(update_fields=["actual_end_date", "updated_at"])
        LeaveAttendanceSyncOutbox.objects.create(
            request=req, application=app, user_id=app.user_id,
            payload={
                "application_id": app.pk,
                "approved_start_date": app.start_date.isoformat(),
                "approved_end_date": effective_end.isoformat(),
                "actual_end_date": req.actual_resumption_date.isoformat(),
                "balance_adjustment_days": delta,
                "category": app.category,
            },
        )
    try:
        notifications.notify_user(app.user_id, f"Leave {req.kind} decision recorded",
                                  f"Your {req.kind} request {req.pk} was {req.status}. {note}")
    except Exception:
        pass
    return req


@transaction.atomic
def withdraw_lifecycle_request(*, request_id, actor, note=""):
    req = LeaveLifecycleRequest.objects.select_for_update().select_related("application").filter(
        pk=request_id, application__user_id=actor.user_id,
        status__in=["pending", "awaiting_substitute", "applicant_action_required"],
    ).first()
    if req is None:
        raise NotFoundError("No pending lifecycle request is available to withdraw.")
    old = req.status
    old_assignee = req.current_assignee_user_id
    req.status = "withdrawn"
    req.current_assignee_user_id = None
    req.save(update_fields=["status", "current_assignee_user_id", "updated_at"])
    LeaveLifecycleEvent.objects.create(
        request=req, from_status=old, to_status="withdrawn",
        action="withdraw", actor_user_id=actor.user_id, note=note,
    )
    if req.kind == "cancellation":
        app = LeaveApplication.objects.select_for_update().get(pk=req.application_id)
        app.status = "approved"
        app.save(update_fields=["status", "updated_at"])
    if old_assignee and old_assignee != actor.user_id:
        try:
            notifications.notify_user(old_assignee, "Leave lifecycle request withdrawn",
                                      f"Request {req.pk} was withdrawn; no further action is required.")
        except Exception:
            pass
    if req.substitute_user_id and req.substitute_user_id != actor.user_id:
        try:
            notifications.notify_user(req.substitute_user_id, "Leave extension withdrawn",
                                      f"Extension request {req.pk} was withdrawn.")
        except Exception:
            pass
    return req
