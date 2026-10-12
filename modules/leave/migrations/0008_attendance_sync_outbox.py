import django.db.models.deletion
from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0007_actual_leave_end")]
    operations = [
        migrations.CreateModel(name="LeaveAttendanceSyncOutbox", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("user_id", models.BigIntegerField(db_index=True)),
            ("payload", models.JSONField(default=dict)),
            ("status", models.CharField(max_length=12, default="pending", db_index=True, choices=[("pending","Pending"),("processed","Processed"),("failed","Failed")])),
            ("attempts", models.PositiveSmallIntegerField(default=0)),
            ("last_error", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("processed_at", models.DateTimeField(null=True, blank=True)),
            ("application", models.ForeignKey(to="leave.leaveapplication", on_delete=django.db.models.deletion.PROTECT, related_name="attendance_sync_events")),
            ("request", models.OneToOneField(to="leave.leavelifecyclerequest", on_delete=django.db.models.deletion.PROTECT, related_name="attendance_sync")),
        ], options={"db_table":"leave_attendance_sync_outbox","ordering":["created_at","id"]}),
    ]
