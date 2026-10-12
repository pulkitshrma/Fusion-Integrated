from django.core.management.base import BaseCommand
from modules.leave.services.sla import process_sla_thresholds


class Command(BaseCommand):
    help = "Process configured ELM pending-task reminders and escalations."

    def handle(self, *args, **options):
        count = process_sla_thresholds()
        self.stdout.write(self.style.SUCCESS(f"ELM SLA events emitted: {count}"))
