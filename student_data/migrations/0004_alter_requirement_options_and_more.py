# Generated by Django 5.2 on 2025-04-12 15:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_data', '0003_student_created_at'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='requirement',
            options={},
        ),
        migrations.RenameField(
            model_name='requirementstudent',
            old_name='date_added',
            new_name='created_at',
        ),
        migrations.AlterUniqueTogether(
            name='requirementstudent',
            unique_together={('student', 'requirement')},
        ),
        migrations.AddField(
            model_name='requirement',
            name='schedule_status',
            field=models.CharField(choices=[('not_scheduled', 'Not Scheduled'), ('scheduled', 'Scheduled'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='not_scheduled', max_length=20),
        ),
        migrations.AddField(
            model_name='requirementstudent',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='student',
            name='scheduled_requirements',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='student',
            name='total_requirements',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='requirement',
            name='company_code',
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AlterField(
            model_name='requirement',
            name='company_name',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='requirement',
            name='requirement_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='requirement',
            name='students',
            field=models.ManyToManyField(through='student_data.RequirementStudent', to='student_data.student'),
        ),
        migrations.AlterField(
            model_name='requirementstudent',
            name='status',
            field=models.CharField(choices=[('pending', 'Pending'), ('selected', 'Selected'), ('rejected', 'Rejected'), ('on_hold', 'On Hold')], default='pending', max_length=20),
        ),
        migrations.AddIndex(
            model_name='requirementstudent',
            index=models.Index(fields=['status'], name='student_dat_status_c1a160_idx'),
        ),
    ]
