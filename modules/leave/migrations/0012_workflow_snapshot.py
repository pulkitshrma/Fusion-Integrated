from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0011_lifecycle_event_status_length")]
    operations = [
        migrations.AddField(
            model_name="leaveapplication", name="workflow_snapshot",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
