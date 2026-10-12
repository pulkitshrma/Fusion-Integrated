"""Pending-only reminder and escalation processing (EL-UC-021)."""
from django.utils import timezone
from modules.leave.models import LeaveApplication, LeaveLifecycleRequest, LeaveSLAConfig, LeaveSLAEvent
from modules.leave.services.notifications import notify_user


def _process(task, config, *, application=None, lifecycle_request=None, assigned_at=None, now=None):
    now = now or timezone.now()
    if not task.current_assignee_user_id:
        return 0
    assigned_at = assigned_at or task.updated_at
    age_hours = (now - assigned_at).total_seconds() / 3600
    emitted = 0
    event_filter = {"application": application} if application else {"lifecycle_request": lifecycle_request}
    assignment_key = assigned_at.isoformat()
    base_filter = {**event_filter, "details__assignment_updated_at": assignment_key}
    if age_hours >= config.reminder_after_hours and not LeaveSLAEvent.objects.filter(
        **base_filter, event_type="reminder"
    ).exists():
        try:
            notify_user(task.current_assignee_user_id, "Leave action reminder",
                        f"A leave workflow task is still pending. Reference: {task.pk}.")
        except Exception:
            pass
        LeaveSLAEvent.objects.create(**event_filter, event_type="reminder",
            recipient_user_id=task.current_assignee_user_id,
            details={"assignment_updated_at": assignment_key, "task_type": config.task_type})
        emitted += 1
    if (age_hours >= config.escalate_after_hours
        and config.escalation_assignee_user_id
        and not LeaveSLAEvent.objects.filter(**base_filter, event_type="escalation").exists()):
        try:
            notify_user(config.escalation_assignee_user_id, "Leave workflow escalation",
                        f"A leave workflow task exceeded its escalation threshold. Reference: {task.pk}.")
        except Exception:
            pass
        LeaveSLAEvent.objects.create(**event_filter, event_type="escalation",
            recipient_user_id=config.escalation_assignee_user_id,
            details={"assignment_updated_at": assignment_key, "task_type": config.task_type})
        emitted += 1
    return emitted


def process_sla_thresholds(now=None):
    now = now or timezone.now()
    emitted = 0
    configs = {c.task_type: c for c in LeaveSLAConfig.objects.filter(is_active=True)}
    for app in LeaveApplication.objects.filter(
        status__in=["awaiting_substitute", "applicant_action_required", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction"],
        current_assignee_user_id__isnull=False,
    ):
        config = configs.get(app.status)
        if config:
            emitted += _process(app, config, application=app, now=now)
    for req in LeaveLifecycleRequest.objects.filter(
        status__in=["pending", "awaiting_substitute", "applicant_action_required"],
        current_assignee_user_id__isnull=False,
    ):
        config = configs.get(f"lifecycle:{req.kind}") or configs.get(req.status)
        if config:
            emitted += _process(req, config, lifecycle_request=req, now=now)
    return emitted
