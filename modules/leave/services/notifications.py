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
