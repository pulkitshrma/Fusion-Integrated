import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0001_initial")]
    operations = [
        migrations.CreateModel(name="LeaveWorkflowStep", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("category", models.CharField(max_length=3)), ("organizational_unit", models.CharField(max_length=120, blank=True)),
            ("designation", models.CharField(max_length=120, blank=True)), ("sequence", models.PositiveSmallIntegerField()),
            ("step_type", models.CharField(max_length=20)), ("assignee_user_id", models.BigIntegerField(null=True, blank=True)),
            ("assignee_role", models.CharField(max_length=80, blank=True)), ("is_active", models.BooleanField(default=True)),
        ], options={"db_table":"leave_workflow_step", "ordering":["category","organizational_unit","designation","sequence"]}),
        migrations.CreateModel(name="LeaveVacationPeriod", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("external_id", models.CharField(max_length=120, unique=True)), ("name", models.CharField(max_length=160)),
            ("start_date", models.DateField()), ("end_date", models.DateField()),
            ("academic_year", models.CharField(max_length=20, db_index=True)), ("is_active", models.BooleanField(default=True)),
        ], options={"db_table":"leave_vacation_period"}),
        migrations.CreateModel(name="LeaveLifecycleRequest", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("kind", models.CharField(max_length=16)), ("status", models.CharField(max_length=12, default="pending")),
            ("requested_start_date", models.DateField(null=True, blank=True)), ("requested_end_date", models.DateField(null=True, blank=True)),
            ("actual_resumption_date", models.DateField(null=True, blank=True)), ("details", models.TextField(blank=True)),
            ("substitute_user_id", models.BigIntegerField(null=True, blank=True)), ("substitute_response", models.CharField(max_length=10, blank=True)),
            ("current_assignee_user_id", models.BigIntegerField(null=True, blank=True, db_index=True)),
            ("current_step_type", models.CharField(max_length=20, blank=True)),
            ("final_decision_by_user_id", models.BigIntegerField(null=True, blank=True)),
            ("final_decision_at", models.DateTimeField(null=True, blank=True)), ("decision_note", models.TextField(blank=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.PROTECT, related_name="lifecycle_requests")),
        ], options={"db_table":"leave_lifecycle_request"}),
        migrations.CreateModel(name="LeaveSLAConfig", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("task_type", models.CharField(max_length=32, unique=True)), ("reminder_after_hours", models.PositiveIntegerField()),
            ("escalate_after_hours", models.PositiveIntegerField()),
            ("escalation_assignee_user_id", models.BigIntegerField(null=True, blank=True)), ("is_active", models.BooleanField(default=True)),
        ], options={"db_table":"leave_sla_config"}),
        migrations.CreateModel(name="LeaveSLAEvent", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("event_type", models.CharField(max_length=16)), ("recipient_user_id", models.BigIntegerField()),
            ("details", models.JSONField(default=dict, blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.CASCADE, null=True, blank=True, related_name="sla_events")),
            ("lifecycle_request", models.ForeignKey(to="leave.leavelifecyclerequest", on_delete=django.db.models.deletion.CASCADE, null=True, blank=True, related_name="sla_events")),
        ], options={"db_table":"leave_sla_event"}),
        migrations.CreateModel(name="LeaveLifecycleEvent", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("from_status", models.CharField(max_length=12, blank=True)), ("to_status", models.CharField(max_length=12)),
            ("action", models.CharField(max_length=32)), ("actor_user_id", models.BigIntegerField(null=True, blank=True)),
            ("note", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("request", models.ForeignKey(to="leave.leavelifecyclerequest", on_delete=django.db.models.deletion.CASCADE, related_name="events")),
        ], options={"db_table":"leave_lifecycle_event", "ordering":["created_at","id"]}),
        migrations.AddIndex(model_name="leavecalendar", index=models.Index(fields=["year","kind","is_published"], name="leave_cal_pub_idx")),
        migrations.AddIndex(model_name="leavebalance", index=models.Index(fields=["user_id","year"], name="leave_balance_user_year_idx")),
        migrations.AddConstraint(model_name="leavebalance", constraint=models.UniqueConstraint(fields=("user_id","category","year"), name="leave_balance_user_cat_year")),
        migrations.AddIndex(model_name="leaveapplication", index=models.Index(fields=["user_id","status"], name="leave_app_user_status_idx")),
        migrations.AddIndex(model_name="leaveapplication", index=models.Index(fields=["current_assignee_user_id","status"], name="leave_app_assignee_idx")),
        migrations.AddConstraint(model_name="leaveapplication", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="leave_period_valid")),
        migrations.AddConstraint(model_name="leaveworkflowstep", constraint=models.UniqueConstraint(fields=("category","organizational_unit","designation","sequence"), name="leave_workflow_step_unique")),
        migrations.AddConstraint(model_name="leavevacationperiod", constraint=models.CheckConstraint(condition=models.Q(("end_date__gte", models.F("start_date"))), name="leave_vacation_period_valid")),
        migrations.AddIndex(model_name="leavelifecyclerequest", index=models.Index(fields=["current_assignee_user_id","status"], name="leave_lifecycle_assignee_idx")),
    ]
