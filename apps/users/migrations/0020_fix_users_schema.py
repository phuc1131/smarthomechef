from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0019_add_userprofile_budget_limit'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='email',
            field=models.EmailField(max_length=255, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='role',
            field=models.CharField(default='user', max_length=50),
        ),
        migrations.AlterField(
            model_name='account',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
