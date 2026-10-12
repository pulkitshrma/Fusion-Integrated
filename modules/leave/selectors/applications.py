from modules.leave.models import LeaveApplication, LeaveBalance

def own_applications(user_id):
    return LeaveApplication.objects.filter(user_id=user_id).order_by("-created_at")

def own_balances(user_id, year):
    return LeaveBalance.objects.filter(user_id=user_id, year=year).order_by("category")

def assigned_inbox(user_id):
    return LeaveApplication.objects.filter(
        current_assignee_user_id=user_id,
        status__in=["awaiting_unit_head", "awaiting_establishment", "awaiting_sanction"],
    ).order_by("created_at")
