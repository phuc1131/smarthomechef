from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_delete_chatmessage_remove_mealplan_food_and_more'),
        ('users', '0016_alter_account_email_alter_account_role_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mealplan',
            name='account',
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column='account_id',
                on_delete=django.db.models.deletion.CASCADE,
                to='users.account',
            ),
        ),
    ]
