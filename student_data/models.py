from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save,post_delete
from django.dispatch import receiver


class Requirement(models.Model):
    SCHEDULE_STATUS_CHOICES = [
        ('not_scheduled', 'Not Scheduled'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]
    
    company_name = models.CharField(max_length=100)
    company_code = models.CharField(max_length=20, blank=False, unique=True)  # Added unique=True
    
    requirement_date = models.DateField(null=True, blank=True)
    is_scheduled = models.BooleanField(default=False)
    schedule_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    schedule_status = models.CharField(
        max_length=20, 
        choices=SCHEDULE_STATUS_CHOICES,
        default='not_scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    students = models.ManyToManyField('Student', through='RequirementStudent')
    schedule_time = models.TimeField(null=True, blank=True)

    def __str__(self):
        return "self.company_name"

    def update_student_counts(self):
        """Update counts for all students in this requirement"""
        students = self.students.all()
        for student in students:
            student.update_requirement_counts()

    @property
    def is_scheduled_today(self):
        return self.schedule_date == timezone.now().date()
    

from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver

class Student(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female')
    ]

    name = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    degree = models.CharField(max_length=50)
    stream = models.CharField(max_length=50)
    yop = models.IntegerField(verbose_name="Year of Passing")
    tenth_percent = models.FloatField(verbose_name="10th Percentage")
    twelfth_percent = models.FloatField(verbose_name="12th Percentage")
    degree_percent = models.FloatField(verbose_name="Degree Percentage")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    type_of_data = models.CharField(max_length=50)
    created_at = models.DateTimeField(default=timezone.now)

    # ✅ These are now stored in the DB
    total_requirements = models.IntegerField(default=0)
    scheduled_requirements = models.IntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['gender']),
            models.Index(fields=['degree']),
        ]

    def __str__(self):
        return self.name

    def update_requirement_counts(self):
        """Update both total and scheduled requirement counts"""
        from .models import RequirementStudent  # Avoid circular import

        requirements = RequirementStudent.objects.filter(student=self)
        self.total_requirements = requirements.count()
        self.scheduled_requirements = requirements.filter(
            requirement__schedule_status='scheduled'
        ).count()
        self.save(update_fields=['total_requirements', 'scheduled_requirements'])


class RequirementStudent(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
        ('on_hold', 'On Hold')
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'requirement']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.requirement.company_name}"

# Signal to track requirement schedule status changes
@receiver(pre_save, sender=Requirement)
def track_schedule_status_change(sender, instance, **kwargs):
    """Track if schedule status is changing"""
    if instance.pk:  # If this is an existing requirement
        old_instance = Requirement.objects.get(pk=instance.pk)
        if old_instance.schedule_status != instance.schedule_status:
            # Store the old status temporarily
            instance._old_status = old_instance.schedule_status
    else:
        instance._old_status = None

@receiver(post_save, sender=Requirement)
def update_student_counts_on_schedule_change(sender, instance, **kwargs):
    """Update all associated students' counts when requirement schedule changes"""
    old_status = getattr(instance, '_old_status', None)
    
    if old_status != instance.schedule_status:
        # Schedule status has changed, update all associated students
        instance.update_student_counts()

# Signals for RequirementStudent changes
@receiver(post_save, sender=RequirementStudent)
def update_counts_on_requirement_student_change(sender, instance, created, **kwargs):
    """Update student counts when a requirement is added or updated"""
    instance.student.update_requirement_counts()

@receiver(post_delete, sender=RequirementStudent)
def update_counts_on_requirement_student_delete(sender, instance, **kwargs):
    """Update student counts when a requirement is removed"""
    instance.student.update_requirement_counts()