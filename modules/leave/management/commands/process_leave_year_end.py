from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from modules.leave.services.year_end import process_year_end


class Command(BaseCommand):
    help = "Run ELM year-end carry-forward, lapse and VL-to-EL conversion."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True,
                            help="Completed leave year, e.g. 2026.")

    def handle(self, *args, **options):
        year = options["year"]
        if year >= timezone.localdate().year:
            raise CommandError("The year-end processor accepts only a completed leave year.")
        run = process_year_end(year)
        self.stdout.write(self.style.SUCCESS(
            f"ELM year-end {year}: {run.status}; "
            f"{run.processed_accounts} accounts; {run.exception_count} exceptions."
        ))
        if run.exceptions:
            for error in run.exceptions:
                self.stderr.write(str(error))
            raise CommandError("Year-end processing completed with exceptions; inspect the run record.")
