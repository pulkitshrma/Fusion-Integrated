"""Transactional ELM application operations. Authorization and routing fail closed."""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.leave.domain import rules
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    LeaveApplication, LeaveApplicationEvent, LeaveBalance, LeaveCalendar,
    LeaveLedgerEntry, LeavePolicy, LeaveSubstituteResponse,
    LeaveVacationPeriod,
)
from modules.leave.services import workflow


PENDING = {
    "awaiting_substitute", "applicant_action_required", "awaiting_unit_head",
    "awaiting_establishment", "awaiting_sanction",
}


def _calendar_dates(start, end, kind):
    rows = LeaveCalendar.objects.filter(
        year__gte=start.year, year__lte=end.year, kind=kind, is_published=True
    )
    return {date.fromisoformat(value) for row in rows for value in row.dates}


def _working_days(start, end, closed):
    total, cursor = 0, start
    while cursor <= end:
        if cursor.weekday() < 5 and cursor not in closed:
            total += 1
        cursor += timedelta(days=1)
    return Decimal(total)


def _requested_days(category, start, end, half_day):
    if category == "CL" and half_day:
        if start != end:
            raise rules.PolicyViolation("invalid_half_day", "Half-day CL must be for one date.")
        return Decimal("0.5")
    if category in {"CL", "SCL"}:
        return _working_days(start, end, _calendar_dates(start, end, "holiday"))
    if category == "RH":
        return Decimal("1")
    return Decimal((end - start).days + 1)


def _validate_overlap(user_id, start, end, category, half_day):
    rows = LeaveApplication.objects.filter(
        user_id=user_id, status__in=[*PENDING, "approved", "cancellation_pending", "extension_pending"],
        start_date__lte=end, end_date__gte=start,
    )
    existing = [{
        "start": row.start_date, "end": row.end_date, "category": row.category,
        "half_day": row.half_day,
    } for row in rows]
    rules.validate_overlap(start, end, existing, half_day=half_day, category=category)


def _employee_kind(user_id):
    person = get_users([user_id]).get(user_id)
    if person is None:
        raise rules.PolicyViolation("employee_not_found", "Employee record was not found in the institute directory.")
    kind = (person.kind or "").lower()
    if kind not in {"faculty", "staff"}:
        raise rules.PolicyViolation("employee_kind_unavailable", "The directory does not identify this employee as Faculty or Staff.")
    return kind


def _balance_for_update(user_id, category, year):
    policy = LeavePolicy.objects.filter(category=category, is_active=True).first()
    if policy is None:
        raise rules.PolicyViolation("policy_missing", f"No active policy is configured for {category}.")
    balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id, category=category, year=year,
        defaults={"credited": policy.annual_entitlement},
    )
    return balance


def _validate_substitute(*, applicant_id, substitute_id, start, end):
    if not substitute_id or substitute_id == applicant_id:
        raise rules.PolicyViolation("invalid_substitute", "A substitute must be another employee.")
    person = get_users([substitute_id]).get(substitute_id)
    if person is None or person.kind not in {"faculty", "staff"}:
        raise rules.PolicyViolation("invalid_substitute", "The nominated substitute must be another institute employee.")
    conflict = LeaveApplication.objects.filter(
        user_id=substitute_id, status__in=[*PENDING, "approved"],
        start_date__lte=end, end_date__gte=start,
    ).exists()
    if conflict:
        raise rules.PolicyViolation("substitute_unavailable", "The nominated substitute has overlapping pending or approved leave.")


@transaction.atomic
def apply(*, actor, category, start_date, end_date, purpose,
          half_day="", station_leave_required=False, station_leave_details=None,
          substitute_user_id=None):
    user_id = actor.user_id
    employee_kind = _employee_kind(user_id)  # never trust a request-body employee_kind
    rules.validate_category(category, employee_kind)
    if end_date < start_date:
        raise rules.PolicyViolation("invalid_period", "End date must not precede start date.")
    if category == "RH":
        rules.validate_rh(start_date, end_date, _calendar_dates(start_date, end_date, "rh"))
    if category == "VL":
        periods = list(LeaveVacationPeriod.objects.filter(
            is_active=True, start_date__lte=start_date, end_date__gte=end_date
        ).values_list("start_date", "end_date"))
        rules.validate_vacation(start_date, end_date, periods)
    if station_leave_required and not station_leave_details:
        raise rules.PolicyViolation("station_leave_details_required", "Station Leave details are required when Station Leave is requested.")
    if not station_leave_required and station_leave_details:
        raise rules.PolicyViolation("station_leave_not_requested", "Station Leave details require Station Leave to be selected.")
    _validate_overlap(user_id, start_date, end_date, category, half_day)
    if substitute_user_id:
        _validate_substitute(applicant_id=user_id, substitute_id=substitute_user_id,
                             start=start_date, end=end_date)
    days = _requested_days(category, start_date, end_date, half_day)
    balance = _balance_for_update(user_id, category, start_date.year)
    if balance.available < days:
        raise rules.PolicyViolation("insufficient_balance", "Available leave balance is insufficient.")
    status = sm.AWAITING_SUBSTITUTE if substitute_user_id else sm.AWAITING_UNIT_HEAD
    app = LeaveApplication.objects.create(
        user_id=user_id, category=category, start_date=start_date, end_date=end_date,
        half_day=half_day, purpose=purpose, employee_kind=employee_kind,
        requested_days=days, status=status,
        station_leave_required=station_leave_required,
        station_leave_details=station_leave_details or {},
        substitute_user_id=substitute_user_id,
    )
    if not substitute_user_id:
        app.current_assignee_user_id = workflow.initial_assignee(app)
        app.save(update_fields=["current_assignee_user_id", "updated_at"])
    LeaveApplicationEvent.objects.create(
        application=app, from_status="", to_status=status, action="submit",
        actor_user_id=user_id,
    )
    return app


@transaction.atomic
def respond_substitute(*, application_id, actor, accept, note=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, substitute_user_id=actor.user_id,
        status=sm.AWAITING_SUBSTITUTE,
    ).first()
    if app is None:
        raise NotFoundError("No pending substitute request assigned to you.")
    old = app.status
    app.substitute_response = "accepted" if accept else "declined"
    app.status = sm.AWAITING_UNIT_HEAD if accept else sm.APPLICANT_ACTION_REQUIRED
    app.current_assignee_user_id = workflow.initial_assignee(app) if accept else None
    app.save(update_fields=["substitute_response", "status", "current_assignee_user_id", "updated_at"])
    LeaveSubstituteResponse.objects.create(
        application=app, substitute_user_id=actor.user_id,
        response=app.substitute_response, note=note,
    )
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="substitute_accept" if accept else "substitute_decline",
        actor_user_id=actor.user_id, note=note,
    )
    return app


@transaction.atomic
def nominate_replacement(*, application_id, actor, substitute_user_id):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id,
        status=sm.APPLICANT_ACTION_REQUIRED,
    ).first()
    if app is None:
        raise NotFoundError("No leave request requires substitute replacement.")
    if app.substitute_response != "declined":
        raise ConflictError("A replacement is allowed only after a substitute declines.", code="replacement_not_allowed")
    _validate_substitute(applicant_id=app.user_id, substitute_id=substitute_user_id,
                         start=app.start_date, end=app.end_date)
    old = app.status
    app.substitute_user_id = substitute_user_id
    app.substitute_response = ""
    app.status = sm.AWAITING_SUBSTITUTE
    app.save(update_fields=["substitute_user_id", "substitute_response", "status", "updated_at"])
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="nominate_replacement", actor_user_id=actor.user_id,
    )
    return app


@transaction.atomic
def decide(*, application_id, actor, outcome, note=""):
    app = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status not in {sm.AWAITING_UNIT_HEAD, sm.AWAITING_ESTABLISHMENT, sm.AWAITING_SANCTION}:
        raise ConflictError("This request is not awaiting a decision.", code="not_actionable")
    if app.current_assignee_user_id != actor.user_id:
        raise PermissionDeniedError("Only the currently assigned workflow actor may process this request.")
    steps = workflow.route_steps(app)
    current = next((s for s in steps if s.assignee_user_id == actor.user_id), None)
    if current is None:
        raise PermissionDeniedError("You are not part of this application's configured approval route.")
    old = app.status
    final = False
    if current.step_type == "unit_head":
        if app.category in {"CL", "RH"}:
            if outcome not in {"approve", "reject"}:
                raise ConflictError("Unit Head must make the final CL/RH decision.", code="invalid_decision")
            final = True
        else:
            if outcome not in {"recommended", "not_recommended"}:
                raise ConflictError("Unit Head must record Recommended or Not Recommended.", code="invalid_recommendation")
            # Not Recommended is explicitly not a final rejection.
    elif current.step_type == "establishment":
        if outcome != "route":
            raise ConflictError("Establishment processing can only route the request onward.", code="invalid_establishment_action")
    elif current.step_type == "sanction":
        if outcome not in {"approve", "reject"}:
            raise ConflictError("Sanctioning Authority must approve or reject.", code="invalid_decision")
        final = True
    else:
        raise ConflictError("Unsupported workflow step.", code="invalid_workflow_step")

    if final:
        app.status = sm.APPROVED if outcome == "approve" else sm.REJECTED
        app.final_decision_by_user_id = actor.user_id
        app.final_decision_at = timezone.now()
        app.decision_note = note
        app.current_assignee_user_id = None
    else:
        next_step = workflow.next_step(app, actor.user_id)
        if next_step is None:
            raise ConflictError("The configured route has no next Sanctioning Authority.", code="workflow_route_incomplete")
        app.status = {
            "unit_head": sm.AWAITING_ESTABLISHMENT if next_step.step_type == "establishment" else sm.AWAITING_SANCTION,
            "establishment": sm.AWAITING_SANCTION,
            "sanction": sm.AWAITING_SANCTION,
        }[next_step.step_type]
        app.current_assignee_user_id = next_step.assignee_user_id
        app.decision_note = note
    app.save()
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action=outcome, actor_user_id=actor.user_id, note=note,
    )
    if app.status == sm.APPROVED:
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=app.user_id, category=app.category, year=app.start_date.year)
        balance.consumed += app.requested_days
        balance.save(update_fields=["consumed", "updated_at"])
        LeaveLedgerEntry.objects.create(
            user_id=app.user_id, application=app, category=app.category,
            amount=app.requested_days, entry_type="debit",
        )
    return app


@transaction.atomic
def withdraw(*, application_id, actor):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id).first()
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status not in PENDING:
        raise ConflictError("Only a pending request can be withdrawn.", code="not_withdrawable")
    old = app.status
    app.status = sm.WITHDRAWN
    app.current_assignee_user_id = None
    app.save(update_fields=["status", "current_assignee_user_id", "updated_at"])
    LeaveApplicationEvent.objects.create(
        application=app, from_status=old, to_status=app.status,
        action="withdraw", actor_user_id=actor.user_id,
    )
    return app
