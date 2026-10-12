from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("leave", "0009_col_evidence_reference")]
    operations = [
        migrations.AlterField(
            model_name="leavelifecyclerequest", name="status",
            field=models.CharField(max_length=12, default="pending", choices=[
                ("pending","Pending"), ("awaiting_substitute","Awaiting Substitute"),
                ("applicant_action_required","Applicant Action Required"),
                ("approved","Approved"), ("rejected","Rejected"), ("withdrawn","Withdrawn"),
            ]),
        ),
    ]
