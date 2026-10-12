from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0008_attendance_sync_outbox")]
    operations = [
        migrations.AddField(
            model_name="leavepolicy", name="medical_evidence_required",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="leaveapplication", name="supporting_evidence_reference",
            field=models.CharField(max_length=250, blank=True),
        ),
        migrations.AddField(
            model_name="leavelifecyclerequest", name="supporting_evidence_reference",
            field=models.CharField(max_length=250, blank=True),
        ),
    ]
