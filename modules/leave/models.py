"""ELM-owned tables. Institute identities are plain IAM user_id integers."""
from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    category = models.CharField(max_length=3, unique=True,
        choices=[(x, x) for x in ("CL","RH","SCL","EL","COL","VL")])
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2)
    carry_forward = models.BooleanField(default=False)
    faculty_only = models.BooleanField(default=False)
    non_faculty_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_policy"


class LeaveCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    year = models.PositiveSmallIntegerField(db_index=True)
    kind = models.CharField(max_length=12, choices=[("holiday","Holiday"),("rh","Restricted Holiday")])
    dates = models.JSONField(default=list)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_calendar"
        indexes = [models.Index(fields=["year","kind","is_published"], name="leave_cal_pub_idx")]


class LeaveBalance(TimeStampedModel):
    user_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=3)
    year = models.PositiveSmallIntegerField()
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    consumed = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [models.UniqueConstraint(fields=["user_id","category","year"], name="leave_balance_user_cat_year")]
        indexes = [models.Index(fields=["user_id","year"], name="leave_balance_user_year_idx")]

    @property
    def available(self):
        return self.credited + self.carried_forward - self.consumed


class LeaveApplication(TimeStampedModel):
    CATEGORIES = [(x,x) for x in ("CL","RH","SCL","EL","COL","VL")]
    STATUSES = [(x,x.replace("_"," ").title()) for x in (
        "draft","awaiting_substitute","applicant_action_required","awaiting_unit_head",
        "awaiting_establishment","awaiting_sanction","approved","rejected","withdrawn",
        "cancellation_pending","cancelled","extension_pending","extended",
        "resumption_pending","completed")]
    user_id = models.BigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=12, blank=True,
        choices=[("first_half","First half"),("second_half","Second half")])
    purpose = models.TextField(max_length=2000)
    status = models.CharField(max_length=32, choices=STATUSES, default="draft", db_index=True)
    requested_days = models.DecimalField(max_digits=7, decimal_places=2)
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.JSONField(default=dict, blank=True)
    employee_kind = models.CharField(max_length=12, choices=[("faculty","Faculty"),("staff","Staff")])
    substitute_user_id = models.BigIntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=10, blank=True,
        choices=[("accepted","Accepted"),("declined","Declined")])
    current_assignee_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    final_decision_by_user_id = models.BigIntegerField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)
    parent_application_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [models.Index(fields=["user_id","status"], name="leave_app_user_status_idx"),
                   models.Index(fields=["current_assignee_user_id","status"], name="leave_app_assignee_idx")]
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="leave_period_valid")]


class LeaveApplicationEvent(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    action = models.CharField(max_length=48)
    actor_user_id = models.BigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_event"
        ordering = ["created_at","id"]


class LeaveLedgerEntry(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    application = models.ForeignKey(LeaveApplication, null=True, blank=True, on_delete=models.PROTECT)
    category = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    entry_type = models.CharField(max_length=16, choices=[("credit","Credit"),("debit","Debit"),("restore","Restore"),("lapse","Lapse"),("conversion","Conversion")])
    reference = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_ledger_entry"


class LeaveSubstituteResponse(TimeStampedModel):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="substitute_responses")
    substitute_user_id = models.BigIntegerField(db_index=True)
    response = models.CharField(max_length=10, choices=[("accepted","Accepted"),("declined","Declined")])
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "leave_substitute_response"


class LeaveWorkflowStep(TimeStampedModel):
    """Explicit, administrator-configured approval route.

    A route is selected by category and (optionally) employee unit/designation.
    A missing next step is a configuration error: requests are never silently
    assigned to nobody or approved by a generic permission holder.
    """
    STEP_TYPES = [("unit_head", "Unit Head"), ("establishment", "Establishment"),
                  ("sanction", "Sanctioning Authority")]
    category = models.CharField(max_length=3, choices=LeaveApplication.CATEGORIES)
    organizational_unit = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    sequence = models.PositiveSmallIntegerField()
    step_type = models.CharField(max_length=20, choices=STEP_TYPES)
    assignee_user_id = models.BigIntegerField(null=True, blank=True)
    assignee_role = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_workflow_step"
        ordering = ["category", "organizational_unit", "designation", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "organizational_unit", "designation", "sequence"],
                name="leave_workflow_step_unique"),
        ]


class LeaveVacationPeriod(TimeStampedModel):
    """Locally cached vacation windows imported from the external Academic Calendar."""
    external_id = models.CharField(max_length=120, unique=True)
    name = models.CharField(max_length=160)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=20, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_vacation_period"
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")),
                                   name="leave_vacation_period_valid"),
        ]


class LeaveLifecycleRequest(TimeStampedModel):
    """Cancellation, extension and resumption are separate audited requests.

    The approved base application is not mutated while a cancellation or
    extension is awaiting a decision.
    """
    KINDS = [("cancellation", "Cancellation"), ("extension", "Extension"),
             ("resumption", "Resumption")]
    STATUSES = [("pending", "Pending"), ("approved", "Approved"),
                ("rejected", "Rejected")]
    application = models.ForeignKey(LeaveApplication, on_delete=models.PROTECT,
                                    related_name="lifecycle_requests")
    kind = models.CharField(max_length=16, choices=KINDS)
    status = models.CharField(max_length=12, choices=STATUSES, default="pending")
    requested_start_date = models.DateField(null=True, blank=True)
    requested_end_date = models.DateField(null=True, blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    details = models.TextField(blank=True)
    substitute_user_id = models.BigIntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=10, blank=True)
    current_assignee_user_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    final_decision_by_user_id = models.BigIntegerField(null=True, blank=True)
    final_decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "leave_lifecycle_request"
        indexes = [models.Index(fields=["current_assignee_user_id", "status"],
                                name="leave_lifecycle_assignee_idx")]


class LeaveSLAConfig(TimeStampedModel):
    """Thresholds are configured in hours for each actionable task class."""
    task_type = models.CharField(max_length=32, unique=True)
    reminder_after_hours = models.PositiveIntegerField()
    escalate_after_hours = models.PositiveIntegerField()
    escalation_assignee_user_id = models.BigIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_sla_config"


class LeaveSLAEvent(models.Model):
    lifecycle_request = models.ForeignKey(LeaveLifecycleRequest, null=True, blank=True,
        on_delete=models.CASCADE, related_name="sla_events")
    application = models.ForeignKey(LeaveApplication, null=True, blank=True,
        on_delete=models.CASCADE, related_name="sla_events")
    event_type = models.CharField(max_length=16, choices=[("assigned","Assigned"),
        ("reminder","Reminder"),("escalation","Escalation")])
    recipient_user_id = models.BigIntegerField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_sla_event"


class LeaveLifecycleEvent(models.Model):
    request = models.ForeignKey(LeaveLifecycleRequest, on_delete=models.CASCADE,
                                related_name="events")
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    action = models.CharField(max_length=32)
    actor_user_id = models.BigIntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_lifecycle_event"
        ordering = ["created_at", "id"]
