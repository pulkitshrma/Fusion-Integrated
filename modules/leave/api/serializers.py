from rest_framework import serializers
from modules.leave.models import (
    LeaveApplication, LeaveApplicationEvent, LeaveBalance, LeaveCalendar,
    LeaveLedgerEntry, LeaveLifecycleEvent, LeaveLifecycleRequest, LeavePolicy, LeaveSLAConfig,
    LeaveWorkflowStep,
)


class LeaveApplicationEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplicationEvent
        fields = ("from_status", "to_status", "action", "actor_user_id", "note", "created_at")


class LeaveLifecycleEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLifecycleEvent
        fields = ("from_status", "to_status", "action", "actor_user_id", "note", "created_at")


class LeaveApplicationSerializer(serializers.ModelSerializer):
    events = LeaveApplicationEventSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ("id", "user_id", "category", "start_date", "end_date", "actual_end_date", "half_day", "purpose", "supporting_evidence_reference",
            "status", "requested_days", "station_leave_required", "station_leave_details",
            "substitute_user_id", "substitute_response", "current_assignee_user_id",
            "final_decision_by_user_id", "final_decision_at", "decision_note",
            "events", "created_at", "updated_at")
        read_only_fields = fields


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=("", "first_half", "second_half"),
                                       required=False, allow_blank=True)
    purpose = serializers.CharField(max_length=2000)
    supporting_evidence_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    station_leave_required = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.DictField(required=False, default=dict)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ReplacementSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField(min_value=1)


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("approve", "reject", "recommended",
                                               "not_recommended", "route"))
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    class Meta:
        model = LeaveBalance
        fields = ("category", "year", "employee_kind", "credited", "carried_forward", "consumed", "available")


class LifecycleRequestSerializer(serializers.ModelSerializer):
    events = LeaveLifecycleEventSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveLifecycleRequest
        fields = ("id", "application_id", "kind", "status", "requested_start_date",
                  "requested_end_date", "actual_resumption_date", "details",
                  "supporting_evidence_reference", "current_assignee_user_id", "final_decision_by_user_id",
                  "final_decision_at", "decision_note", "events", "created_at", "updated_at")
        read_only_fields = fields


class CancellationSerializer(serializers.Serializer):
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ExtensionSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    details = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    supporting_evidence_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    details = serializers.CharField(max_length=2000, required=True, allow_blank=False)


class LifecycleDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "category", "annual_entitlement", "carry_forward",
                  "faculty_only", "non_faculty_only", "medical_evidence_required", "is_active")


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = ("id", "name", "year", "kind", "dates", "is_published",
                  "published_at", "published_by_user_id")
        read_only_fields = ("id", "is_published", "published_at", "published_by_user_id")


class WorkflowStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveWorkflowStep
        fields = ("id", "category", "organizational_unit", "designation",
                  "sequence", "step_type", "assignee_user_id", "assignee_role",
                  "is_active")


class SLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSLAConfig
        fields = ("id", "task_type", "reminder_after_hours",
                  "escalate_after_hours", "escalation_assignee_user_id", "is_active")

    def validate(self, attrs):
        reminder = attrs.get("reminder_after_hours",
                             getattr(self.instance, "reminder_after_hours", None))
        escalation = attrs.get("escalate_after_hours",
                               getattr(self.instance, "escalate_after_hours", None))
        if reminder is None or escalation is None or escalation <= reminder:
            raise serializers.ValidationError(
                "Escalation threshold must be greater than the reminder threshold."
            )
        return attrs


class OfflineSanctionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    sanction_reference = serializers.CharField(max_length=120)
    sanction_date = serializers.DateField()
    station_leave_required = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.DictField(required=False, default=dict)
    supporting_evidence_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)
    supporting_evidence_reference = serializers.CharField(max_length=250, required=False, allow_blank=True)


class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "application_id", "category", "amount", "entry_type",
                  "reference", "created_at")
        read_only_fields = fields


class RecordMaintenanceSerializer(serializers.Serializer):
    purpose = serializers.CharField(max_length=2000, required=False)
    station_leave_details = serializers.DictField(required=False)
    correction_note = serializers.CharField(max_length=1000)


class LifecycleWithdrawSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
