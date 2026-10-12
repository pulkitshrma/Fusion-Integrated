"""Event-triggered year-end leave-account processing (EL-UC-020)."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.leave.domain.rules import year_end_outcome
from modules.leave.models import (
    LeaveBalance, LeaveLedgerEntry, LeavePolicy, LeaveYearEndRun,
)


@transaction.atomic
def process_year_end(year):
    run, created = LeaveYearEndRun.objects.select_for_update().get_or_create(year=year)
    if not created and run.status == "completed":
        return run
    run.status = "running"
    run.exceptions = []
    run.exception_count = 0
    run.processed_accounts = 0
    run.save(update_fields=["status", "exceptions", "exception_count", "processed_accounts"])
    errors = []
    balances = list(LeaveBalance.objects.select_for_update().filter(year=year).order_by("user_id", "category"))
    for balance in balances:
        try:
            unused = balance.available
            outcome = year_end_outcome(balance.category, unused)
            next_year = year + 1
            policy = LeavePolicy.objects.filter(category=balance.category, is_active=True).first()
            if policy is None:
                raise ValueError(f"No active policy for {balance.category}")
            target, _ = LeaveBalance.objects.select_for_update().get_or_create(
                user_id=balance.user_id, category=balance.category, year=next_year,
                defaults={"credited": policy.annual_entitlement},
            )
            if outcome["carry"]:
                target.carried_forward += outcome["carry"]
                LeaveLedgerEntry.objects.create(
                    user_id=balance.user_id, category=balance.category,
                    amount=outcome["carry"], entry_type="credit",
                    reference=f"carry-forward:{year}",
                )
            if outcome["lapse"]:
                LeaveLedgerEntry.objects.create(
                    user_id=balance.user_id, category=balance.category,
                    amount=outcome["lapse"], entry_type="lapse",
                    reference=f"year-end:{year}",
                )
            if outcome["credit_el"]:
                el_policy = LeavePolicy.objects.filter(category="EL", is_active=True).first()
                if el_policy is None:
                    raise ValueError("No active EL policy exists for VL conversion")
                el_balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
                    user_id=balance.user_id, category="EL", year=next_year,
                    defaults={"credited": el_policy.annual_entitlement},
                )
                el_balance.credited += outcome["credit_el"]
                el_balance.save(update_fields=["credited", "updated_at"])
                LeaveLedgerEntry.objects.create(
                    user_id=balance.user_id, category="EL",
                    amount=outcome["credit_el"], entry_type="conversion",
                    reference=f"VL-to-EL:{year}:2-to-1",
                )
            target.save(update_fields=["carried_forward", "updated_at"])
            run.processed_accounts += 1
        except Exception as exc:
            errors.append({"user_id": balance.user_id, "category": balance.category,
                           "error": str(exc)})
    run.exceptions = errors
    run.exception_count = len(errors)
    run.status = "completed" if not errors else "failed"
    run.completed_at = timezone.now()
    run.save(update_fields=["exceptions", "exception_count", "processed_accounts",
                            "status", "completed_at"])
    return run
