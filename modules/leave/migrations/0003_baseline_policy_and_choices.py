from decimal import Decimal
from django.db import migrations, models


def seed_leave_policy(apps, schema_editor):
    Policy = apps.get_model("leave", "LeavePolicy")
    rows = [
        ("CL", "8", False, False, False),
        ("RH", "2", False, False, False),
        ("SCL", "15", False, False, False),
        ("EL", "30", True, False, True),
        ("COL", "20", True, False, False),
        ("VL", "60", False, True, False),
    ]
    for category, entitlement, carry, faculty_only, non_faculty_only in rows:
        Policy.objects.get_or_create(category=category, defaults={
            "annual_entitlement": Decimal(entitlement), "carry_forward": carry,
            "faculty_only": faculty_only, "non_faculty_only": non_faculty_only,
            "is_active": True,
        })


class Migration(migrations.Migration):
    dependencies = [("leave", "0002_workflow_and_lifecycle")]
    operations = [
        migrations.AlterField(model_name="leavepolicy", name="category", field=models.CharField(max_length=3, unique=True, choices=[("CL","CL"),("RH","RH"),("SCL","SCL"),("EL","EL"),("COL","COL"),("VL","VL")])),
        migrations.AlterField(model_name="leavecalendar", name="kind", field=models.CharField(max_length=12, choices=[("holiday","Holiday"),("rh","Restricted Holiday")])),
        migrations.AlterField(model_name="leaveapplication", name="category", field=models.CharField(max_length=3, choices=[("CL","CL"),("RH","RH"),("SCL","SCL"),("EL","EL"),("COL","COL"),("VL","VL")])),
        migrations.AlterField(model_name="leaveapplication", name="half_day", field=models.CharField(max_length=12, blank=True, choices=[("first_half","First half"),("second_half","Second half")])),
        migrations.AlterField(model_name="leaveapplication", name="status", field=models.CharField(max_length=32, default="draft", db_index=True, choices=[(x,x.replace("_"," ").title()) for x in ("draft","awaiting_substitute","applicant_action_required","awaiting_unit_head","awaiting_establishment","awaiting_sanction","approved","rejected","withdrawn","cancellation_pending","cancelled","extension_pending","extended","resumption_pending","completed")])),
        migrations.AlterField(model_name="leaveapplication", name="employee_kind", field=models.CharField(max_length=12, choices=[("faculty","Faculty"),("staff","Staff")])),
        migrations.AlterField(model_name="leaveapplication", name="substitute_response", field=models.CharField(max_length=10, blank=True, choices=[("accepted","Accepted"),("declined","Declined")])),
        migrations.AlterField(model_name="leaveledgerentry", name="entry_type", field=models.CharField(max_length=16, choices=[("credit","Credit"),("debit","Debit"),("restore","Restore"),("lapse","Lapse"),("conversion","Conversion")])),
        migrations.AlterField(model_name="leavesubstituteresponse", name="response", field=models.CharField(max_length=10, choices=[("accepted","Accepted"),("declined","Declined")])),
        migrations.AlterField(model_name="leaveworkflowstep", name="category", field=models.CharField(max_length=3, choices=[("CL","CL"),("RH","RH"),("SCL","SCL"),("EL","EL"),("COL","COL"),("VL","VL")])),
        migrations.AlterField(model_name="leaveworkflowstep", name="step_type", field=models.CharField(max_length=20, choices=[("unit_head","Unit Head"),("establishment","Establishment"),("sanction","Sanctioning Authority")])),
        migrations.AlterField(model_name="leavelifecyclerequest", name="kind", field=models.CharField(max_length=16, choices=[("cancellation","Cancellation"),("extension","Extension"),("resumption","Resumption")])),
        migrations.AlterField(model_name="leavelifecyclerequest", name="status", field=models.CharField(max_length=12, default="pending", choices=[("pending","Pending"),("awaiting_substitute","Awaiting Substitute"),("applicant_action_required","Applicant Action Required"),("approved","Approved"),("rejected","Rejected")])),
        migrations.AlterField(model_name="leaveslaevent", name="event_type", field=models.CharField(max_length=16, choices=[("assigned","Assigned"),("reminder","Reminder"),("escalation","Escalation")])),
        migrations.RunPython(seed_leave_policy, migrations.RunPython.noop),
    ]
