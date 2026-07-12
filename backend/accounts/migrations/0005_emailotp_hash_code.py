"""Store OTP codes as a salted hash instead of plaintext.

Existing rows hold plaintext in `code` that can't be rehashed, but OTPs are
ephemeral (single-use, ~10-min lifetime), so any pending ones are safe to drop
— the user simply requests a fresh code. We clear the table, then swap the
`code` column for `code_hash`.
"""

from django.db import migrations, models


def clear_otps(apps, schema_editor):
    apps.get_model("accounts", "EmailOTP").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_devicetoken"),
    ]

    operations = [
        migrations.RunPython(clear_otps, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="emailotp",
            name="code",
        ),
        migrations.AddField(
            model_name="emailotp",
            name="code_hash",
            field=models.CharField(default="", max_length=128),
            preserve_default=False,
        ),
    ]
