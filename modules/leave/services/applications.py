"""Transactional ELM application and decision operations."""
from datetime import date, timedelta
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.leave.domain import rules
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    LeaveApplication, LeaveApplicationEvent, LeaveBalance, LeaveCalendar,
    LeaveLedgerEntry, LeavePolicy,
)


def _calendar_dates(year, kind):
    rows = LeaveCalendar.objects.filter(year=year, kind=kind, is_published=True)
    return {date.fromisoformat(x) for row in rows for x in row.dates}


def _working_days(start, end, closed):
    count, cursor = 0, start
    while cursor <= end:
        if cursor.weekday() < 5 and cursor not in closed:
            count += 1
        cursor += timedelta(days=1)
    return Decimal(count)


def _requested_days(category, start, end, half_day):
    if category == "CL" and half_day:
        if start != end:
            raise rules.PolicyViolation("invalid_half_day", "Half-day CL must be for one date.")
        return Decimal("0.5")
    if category in {"CL","SCL","RH"}:
        return _working_days(start, end, _calendar_dates(start.year, "holiday"))
    return Decimal((end-start).days + 1)


def _validate_overlap(user_id, start, end, category, half_day):
    qs = LeaveApplication.objects.filter(user_id=user_id, status__in=[
        "awaiting_substitute","applicant_action_required","awaiting_unit_head",
        "awaiting_establishment","awaiting_sanction","approved",
        "cancellation_pending","extension_pending"
    ], start_date__lte=end, end_date__gte=start)
    for item in qs:
        distinct_halves = (category == item.category == "CL" and start == end
            == item.start_date == item.end_date and half_day and item.half_day
            and half_day != item.half_day)
        if not distinct_halves:
            raise rules.PolicyViolation("leave_overlap", "The requested dates overlap another pending or approved leave.")


@transaction.atomic
def apply(*, actor, category, start_date, end_date, purpose, employee_kind,
          half_day="", station_leave_required=False, station_leave_details=None,
          substitute_user_id=None):
    rules.validate_category(category, employee_kind)
    if end_date < start_date:
        raise rules.PolicyViolation("invalid_period", "End date must not precede start date.")
    if category == "RH":
        dates = _calendar_dates(start_date.year, "rh")
        rules.validate_rh(start_date, end_date, dates)
    if category == "VL":
        # Academic Calendar is external; until its adapter is configured we fail closed.
        raise rules.PolicyViolation("academic_calendar_unavailable",
            "VL requires vacation-period data from the Academic Calendar service.")
    _validate_overlap(actor.user_id, start_date, end_date, category, half_day)
    days = _requested_days(category, start_date, end_date, half_day)
    policy = LeavePolicy.objects.filter(category=category, is_active=True).first()
    if policy is None:
        raise rules.PolicyViolation("policy_missing", f"No active policy is configured for {category}.")
    balance = LeaveBalance.objects.select_for_update().filter(
        user_id=actor.user_id, category=category, year=start_date.year).first()
    if balance is None or balance.available < days:
        raise rules.PolicyViolation("insufficient_balance", "Available leave balance is insufficient.")
    if substitute_user_id == actor.user_id:
        raise rules.PolicyViolation("invalid_substitute", "Applicant cannot nominate themselves.")
    status = sm.AWAITING_SUBSTITUTE if substitute_user_id else sm.AWAITING_UNIT_HEAD
    app = LeaveApplication.objects.create(
        user_id=actor.user_id, category=category, start_date=start_date,
        end_date=end_date, half_day=half_day, purpose=purpose,
        employee_kind=employee_kind, requested_days=days, status=status,
        station_leave_required=station_leave_required,
        station_leave_details=station_leave_details or {},
        substitute_user_id=substitute_user_id)
    LeaveApplicationEvent.objects.create(application=app, from_status="",
        to_status=status, action="submit", actor_user_id=actor.user_id)
    if not substitute_user_id:
        app.current_assignee_user_id = None
        app.save(update_fields=["current_assignee_user_id","updated_at"])
    return app


@transaction.atomic
def respond_substitute(*, application_id, actor, accept, note=""):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, substitute_user_id=actor.user_id,
        status=sm.AWAITING_SUBSTITUTE).first()
    if app is None:
        raise NotFoundError("No pending substitute request assigned to you.")
    old = app.status
    app.substitute_response = "accepted" if accept else "declined"
    app.status = sm.AWAITING_UNIT_HEAD if accept else sm.APPLICANT_ACTION_REQUIRED
    app.save(update_fields=["substitute_response","status","updated_at"])
    from modules.leave.models import LeaveSubstituteResponse
    LeaveSubstituteResponse.objects.create(application=app,
        substitute_user_id=actor.user_id, response=app.substitute_response, note=note)
    LeaveApplicationEvent.objects.create(application=app, from_status=old,
        to_status=app.status, action="substitute_accept" if accept else "substitute_decline",
        actor_user_id=actor.user_id, note=note)
    return app


@transaction.atomic
def decide(*, application_id, actor, outcome, note="", final=False):
    app = LeaveApplication.objects.select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("No such leave request.")
    old = app.status
    if app.status != sm.AWAITING_UNIT_HEAD and app.status != sm.AWAITING_SANCTION and app.status != sm.AWAITING_ESTABLISHMENT:
        raise ConflictError("This request is not awaiting a decision.", code="not_actionable")
    if app.category in {"CL","RH"} and app.status == sm.AWAITING_UNIT_HEAD:
        if outcome not in {"approve","reject"}:
            raise ConflictError("Unit Head must approve or reject CL/RH.", code="invalid_decision")
        app.status = sm.APPROVED if outcome == "approve" else sm.REJECTED
        final = True
    elif app.status == sm.AWAITING_UNIT_HEAD:
        if outcome not in {"recommended","not_recommended"}:
            raise ConflictError("Unit Head must record Recommended or Not Recommended.", code="invalid_recommendation")
        if outcome == "not_recommended":
            # Not Recommended is a recommendation, not a final rejection.
            app.decision_note = note
            app.status = sm.AWAITING_SANCTION
        else:
            app.status = sm.AWAITING_ESTABLISHMENT
    elif app.status == sm.AWAITING_ESTABLISHMENT:
        app.status = sm.AWAITING_SANCTION
    else:
        if outcome not in {"approve","reject"}:
            raise ConflictError("Final authority must approve or reject.", code="invalid_decision")
        app.status = sm.APPROVED if outcome == "approve" else sm.REJECTED
        final = True
    if final:
        app.final_decision_by_user_id = actor.user_id
        app.final_decision_at = timezone.now()
        app.decision_note = note
    app.save()
    LeaveApplicationEvent.objects.create(application=app, from_status=old,
        to_status=app.status, action=outcome, actor_user_id=actor.user_id, note=note)
    if app.status == sm.APPROVED and old != sm.APPROVED:
        balance = LeaveBalance.objects.select_for_update().get(
            user_id=app.user_id, category=app.category, year=app.start_date.year)
        balance.consumed += app.requested_days
        balance.save(update_fields=["consumed","updated_at"])
        LeaveLedgerEntry.objects.create(user_id=app.user_id, application=app,
            category=app.category, amount=app.requested_days, entry_type="debit")
    return app


@transaction.atomic
def withdraw(*, application_id, actor):
    app = LeaveApplication.objects.select_for_update().filter(
        pk=application_id, user_id=actor.user_id).first()
    if app is None:
        raise NotFoundError("No such leave request.")
    if app.status not in {sm.AWAITING_SUBSTITUTE, sm.APPLICANT_ACTION_REQUIRED,
        sm.AWAITING_UNIT_HEAD, sm.AWAITING_ESTABLISHMENT, sm.AWAITING_SANCTION}:
        raise ConflictError("Only a pending request can be withdrawn.", code="not_withdrawable")
    old = app.status
    app.status = sm.WITHDRAWN
    app.current_assignee_user_id = None
    app.save(update_fields=["status","current_assignee_user_id","updated_at"])
    LeaveApplicationEvent.objects.create(application=app, from_status=old,
        to_status=app.status, action="withdraw", actor_user_id=actor.user_id)
    return app
