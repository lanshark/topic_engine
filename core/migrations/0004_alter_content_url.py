# Generated by Django 5.1.3 on 2024-11-18 00:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_source_error_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='url',
            field=models.URLField(max_length=2000, unique=True),
        ),
    ]
