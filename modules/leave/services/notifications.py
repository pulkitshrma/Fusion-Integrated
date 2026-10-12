"""ELM notifications use institute directory email addresses."""
import logging
from django.conf import settings
from django.core.mail import send_mail
from modules.directory.contracts import get_users

log = logging.getLogger("fusion.leave.notifications")


def notify_user(user_id, subject, message):
    person = get_users([user_id]).get(user_id)
    if person is None or not person.email:
        log.warning("ELM notification skipped: no directory email for user_id=%s", user_id)
        return False
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [person.email], fail_silently=False)
    return True


def notify_application_assignee(application):
    from modules.leave.models import LeaveSLAEvent
    recipient = application.current_assignee_user_id
    if recipient is None:
        return
    try:
        notify_user(recipient, "Leave workflow task assigned",
                    f"A leave request requires your action. Reference: {application.pk}.")
    except Exception:
        log.exception("Could not send ELM assignment notification for application=%s", application.pk)
    LeaveSLAEvent.objects.create(
        application=application, event_type="assigned", recipient_user_id=recipient,
        details={"assignment_updated_at": application.updated_at.isoformat(),
                 "status": application.status},
    )


def notify_substitute(application):
    recipient = application.substitute_user_id
    if recipient is None:
        return
    try:
        notify_user(recipient, "Leave substitute consent requested",
                    f"You have been nominated as a substitute for leave request {application.pk}.")
    except Exception:
        log.exception("Could not send ELM substitute notification for application=%s", application.pk)


def notify_lifecycle_assignee(request):
    from modules.leave.models import LeaveSLAEvent
    recipient = request.current_assignee_user_id
    if recipient is None:
        return
    try:
        notify_user(recipient, "Leave workflow task assigned",
                    f"A {request.kind} request requires your action. Reference: {request.pk}.")
    except Exception:
        log.exception("Could not send ELM lifecycle notification for request=%s", request.pk)
    LeaveSLAEvent.objects.create(
        lifecycle_request=request, event_type="assigned", recipient_user_id=recipient,
        details={"assignment_updated_at": request.updated_at.isoformat(),
                 "status": request.status, "task_type": f"lifecycle:{request.kind}"},
    )
