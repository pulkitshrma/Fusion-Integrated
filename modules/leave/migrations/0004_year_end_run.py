from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0003_baseline_policy_and_choices")]
    operations = [
        migrations.CreateModel(name="LeaveYearEndRun", fields=[
            ("id", models.BigAutoField(primary_key=True, serialize=False, auto_created=True, verbose_name="ID")),
            ("year", models.PositiveSmallIntegerField(unique=True)),
            ("started_at", models.DateTimeField(auto_now_add=True)),
            ("completed_at", models.DateTimeField(null=True, blank=True)),
            ("status", models.CharField(max_length=12, default="running", choices=[("running","Running"),("completed","Completed"),("failed","Failed")])),
            ("processed_accounts", models.PositiveIntegerField(default=0)),
            ("exception_count", models.PositiveIntegerField(default=0)),
            ("exceptions", models.JSONField(default=list, blank=True)),
        ], options={"db_table":"leave_year_end_run"}),
    ]
