# Generated by Django 5.2 on 2025-04-17 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_data', '0008_fix_duplicate_company_codes'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='requirementstudent',
            name='student_dat_status_c1a160_idx',
        ),
        migrations.RemoveField(
            model_name='requirementstudent',
            name='status',
        ),
        migrations.AddField(
            model_name='requirementstudent',
            name='student_status',
            field=models.CharField(choices=[('not_cleared', 'Not Cleared'), ('cleared', 'Cleared')], default='not_cleared', max_length=20),
        ),
    ]
