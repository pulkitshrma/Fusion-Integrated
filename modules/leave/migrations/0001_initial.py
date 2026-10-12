import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="LeavePolicy", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("category", models.CharField(max_length=3, unique=True)),
            ("annual_entitlement", models.DecimalField(max_digits=7, decimal_places=2)),
            ("carry_forward", models.BooleanField(default=False)), ("faculty_only", models.BooleanField(default=False)),
            ("non_faculty_only", models.BooleanField(default=False)), ("is_active", models.BooleanField(default=True)),
        ], options={"db_table":"leave_policy"}),
        migrations.CreateModel(name="LeaveCalendar", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("name", models.CharField(max_length=120)), ("year", models.PositiveSmallIntegerField(db_index=True)),
            ("kind", models.CharField(max_length=12)), ("dates", models.JSONField(default=list)),
            ("is_published", models.BooleanField(default=False)), ("published_at", models.DateTimeField(null=True, blank=True)),
            ("published_by_user_id", models.IntegerField(null=True, blank=True)),
        ], options={"db_table":"leave_calendar"}),
        migrations.CreateModel(name="LeaveBalance", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.BigIntegerField(db_index=True)), ("category", models.CharField(max_length=3)),
            ("year", models.PositiveSmallIntegerField()), ("credited", models.DecimalField(max_digits=8, decimal_places=2, default=0)),
            ("consumed", models.DecimalField(max_digits=8, decimal_places=2, default=0)),
            ("carried_forward", models.DecimalField(max_digits=8, decimal_places=2, default=0)),
        ], options={"db_table":"leave_balance"}),
        migrations.CreateModel(name="LeaveApplication", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("user_id", models.BigIntegerField(db_index=True)), ("category", models.CharField(max_length=3)),
            ("start_date", models.DateField()), ("end_date", models.DateField()),
            ("half_day", models.CharField(max_length=12, blank=True)), ("purpose", models.TextField(max_length=2000)),
            ("status", models.CharField(max_length=32, default="draft", db_index=True)),
            ("requested_days", models.DecimalField(max_digits=7, decimal_places=2)),
            ("station_leave_required", models.BooleanField(default=False)),
            ("station_leave_details", models.JSONField(default=dict, blank=True)),
            ("employee_kind", models.CharField(max_length=12)),
            ("substitute_user_id", models.BigIntegerField(null=True, blank=True)),
            ("substitute_response", models.CharField(max_length=10, blank=True)),
            ("current_assignee_user_id", models.BigIntegerField(null=True, blank=True, db_index=True)),
            ("final_decision_by_user_id", models.BigIntegerField(null=True, blank=True)),
            ("final_decision_at", models.DateTimeField(null=True, blank=True)),
            ("decision_note", models.TextField(blank=True)), ("parent_application_id", models.BigIntegerField(null=True, blank=True)),
        ], options={"db_table":"leave_application"}),
        migrations.CreateModel(name="LeaveApplicationEvent", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("from_status", models.CharField(max_length=32, blank=True)), ("to_status", models.CharField(max_length=32)),
            ("action", models.CharField(max_length=48)), ("actor_user_id", models.BigIntegerField(null=True, blank=True)),
            ("note", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.CASCADE, related_name="events")),
        ], options={"db_table":"leave_application_event", "ordering":["created_at","id"]}),
        migrations.CreateModel(name="LeaveLedgerEntry", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("user_id", models.BigIntegerField(db_index=True)), ("category", models.CharField(max_length=3)),
            ("amount", models.DecimalField(max_digits=8, decimal_places=2)), ("entry_type", models.CharField(max_length=16)),
            ("reference", models.CharField(max_length=120, blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        ], options={"db_table":"leave_ledger_entry"}),
        migrations.CreateModel(name="LeaveSubstituteResponse", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("substitute_user_id", models.BigIntegerField(db_index=True)), ("response", models.CharField(max_length=10)),
            ("note", models.CharField(max_length=500, blank=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.CASCADE, related_name="substitute_responses")),
        ], options={"db_table":"leave_substitute_response"}),
    ]
