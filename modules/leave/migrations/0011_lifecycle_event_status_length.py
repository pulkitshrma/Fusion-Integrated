from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0010_lifecycle_withdrawn")]
    operations = [
        migrations.AlterField(
            model_name="leavelifecycleevent", name="from_status",
            field=models.CharField(max_length=32, blank=True),
        ),
        migrations.AlterField(
            model_name="leavelifecycleevent", name="to_status",
            field=models.CharField(max_length=32),
        ),
    ]
