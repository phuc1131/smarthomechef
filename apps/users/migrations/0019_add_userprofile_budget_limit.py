from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0017_merge_20260505_2228'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='budget_limit',
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text='Budget limit for daily spending'),
        ),
    ]
