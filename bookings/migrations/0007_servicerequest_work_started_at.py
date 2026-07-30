from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0006_servicerequest_arrival_otp_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="servicerequest",
            name="work_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
