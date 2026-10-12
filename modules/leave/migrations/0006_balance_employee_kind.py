from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0005_applicant_role")]
    operations = [
        migrations.AddField(
            model_name="leavebalance", name="employee_kind",
            field=models.CharField(
                max_length=12, default="staff",
                choices=[("faculty", "Faculty"), ("staff", "Staff")],
            ),
        ),
    ]
