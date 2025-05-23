# Generated by Django 5.2 on 2025-04-30 09:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student_data', '0004_remove_requirementsubject_degree_percent_cutoff_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subject',
            name='name',
            field=models.CharField(choices=[('core_java', 'Core Java'), ('advanced_java', 'Advanced Java'), ('web_technology', 'Web Technology'), ('sql', 'SQL'), ('ds_algo', 'Data Structures & Algorithms'), ('python', 'Python'), ('communication', 'Communication Skills'), ('reactjs', 'ReactJS'), ('other', 'Others')], max_length=50, unique=True),
        ),
    ]
