from rest_framework import serializers
from modules.leave.models import LeaveApplication, LeaveBalance


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = ("id","category","start_date","end_date","half_day","purpose",
            "status","requested_days","station_leave_required","station_leave_details",
            "substitute_user_id","substitute_response","created_at","updated_at")
        read_only_fields = ("id","status","requested_days","substitute_response","created_at","updated_at")


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL","RH","SCL","EL","COL","VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=("","first_half","second_half"), required=False, allow_blank=True)
    purpose = serializers.CharField(max_length=2000)
    employee_kind = serializers.ChoiceField(choices=("faculty","staff"))
    station_leave_required = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.DictField(required=False, default=dict)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("approve","reject","recommended","not_recommended","route"))
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    class Meta:
        model = LeaveBalance
        fields = ("category","year","credited","carried_forward","consumed","available")
