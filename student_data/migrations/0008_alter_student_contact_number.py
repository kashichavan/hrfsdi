# Generated by Django 5.2 on 2025-05-25 17:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_data', '0007_requirement_percentage_10th_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='contact_number',
            field=models.CharField(max_length=15, unique=True),
        ),
    ]
