"""Approved-leave cancellation, extension and resumption workflows."""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import rules
from modules.leave.models import (
    LeaveApplication, LeaveApplicationEvent, LeaveBalance, LeaveLedgerEntry,
    LeaveLifecycleEvent, LeaveLifecycleRequest, LeaveVacationPeriod,
)
from modules.leave.services import applications, workflow


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
    if app.lifecycle_requests.filter(kind="cancellation", status__in=["pending", "awaiting_substitute"]).exists():
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
    old = app.status
    app.status = "cancellation_pending"
    app.save(update_fields=["status", "updated_at"])
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="request_cancellation", actor_user_id=actor.user_id, note=details,
    )
    return request


@transaction.atomic
def request_extension(*, application_id, actor, new_end_date, details="", substitute_user_id=None):
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
    increment_start = app.end_date + timedelta(days=1)
    incremental = applications._requested_days(app.category, increment_start, new_end_date, "")
    balance = applications._balance_for_update(app.user_id, app.category, app.start_date.year)
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
        requested_start_date=increment_start, requested_end_date=new_end_date,
        substitute_user_id=substitute_user_id,
        current_assignee_user_id=assignee, current_step_type=step_type,
    )
    LeaveLifecycleEvent.objects.create(
        request=request, from_status="", to_status=request_status,
        action="request_extension", actor_user_id=actor.user_id, note=details,
    )
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
    if app.lifecycle_requests.filter(kind="resumption", status="pending").exists():
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
        required_permission = "leave.workflow.sanction"
    elif req.current_step_type == "unit_head":
        required_permission = "leave.workflow.review"
    else:
        required_permission = "leave.workflow.sanction"
    if not actor.has_permission(required_permission):
        raise PermissionDeniedError(f"This action requires {required_permission}.")
    old = req.status
    final = req.kind == "resumption" or req.current_step_type == "sanction" or (
        req.current_step_type == "unit_head" and app.category in {"CL", "RH"}
    )
    if not final:
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
            action="recommended" if approve else "not_recommended",
            actor_user_id=actor.user_id, note=note,
        )
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
        delta = (req.actual_resumption_date - app.end_date).days
        if delta:
            balance = LeaveBalance.objects.select_for_update().get(
                user_id=app.user_id, category=app.category, year=app.start_date.year)
            amount = Decimal(abs(delta))
            if delta < 0:
                amount = min(balance.consumed, amount)
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
    return req
