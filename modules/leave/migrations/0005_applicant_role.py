from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0004_year_end_run")]
    operations = [
        migrations.AddField(
            model_name="leaveapplication", name="applicant_role",
            field=models.CharField(max_length=80, blank=True),
        ),
    ]
