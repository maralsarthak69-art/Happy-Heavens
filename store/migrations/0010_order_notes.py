from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_newslettersubscriber'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='notes',
            field=models.TextField(
                blank=True,
                default='',
                verbose_name='Your Private Notes',
                help_text=(
                    "Write anything here for yourself — e.g. 'Called customer, delivering Friday' "
                    "or 'Waiting for payment confirmation'. Customers never see this."
                ),
            ),
        ),
    ]
