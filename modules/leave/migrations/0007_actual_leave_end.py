from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0006_balance_employee_kind")]
    operations = [
        migrations.AddField(
            model_name="leaveapplication", name="actual_end_date",
            field=models.DateField(null=True, blank=True),
        ),
    ]
