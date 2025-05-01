from itertools import count
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from datetime import timedelta
from django.db import transaction

class Subject(models.Model):
        """Model to represent fixed subjects that students will be rated on"""
        SUBJECT_CHOICES = [
            ('core_java', 'Core Java'),
            ('advanced_java', 'Advanced Java'),
            ('web_technology', 'Web Technology'),
            ('sql', 'SQL'),
            ('ds_algo', 'Data Structures & Algorithms'),
            ('python', 'Python'),
            ('communication', 'Communication Skills'),
            ('reactjs','ReactJS'),
            ('other',"Other")
        ]
        
        name = models.CharField(max_length=50, choices=SUBJECT_CHOICES, unique=True)
        description = models.TextField(blank=True, null=True)
        is_active = models.BooleanField(default=True)
        created_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        class Meta:
            ordering = ['name']
            verbose_name = 'Subject'
            verbose_name_plural = 'Subjects'

        def __str__(self):
            return self.get_name_display()

class StudentSubjectRating(models.Model):
        """Model to store subject-wise ratings for each student"""
        RATING_CHOICES = [
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('average', 'Average'),
            ('bad', 'Bad'),
        ]
        
        student = models.ForeignKey('Student', on_delete=models.CASCADE, related_name='subject_ratings')
        subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
        rating = models.CharField(max_length=20, choices=RATING_CHOICES)
        remarks = models.TextField(blank=True, null=True)
        evaluated_by = models.CharField(max_length=100, blank=True, null=True)
        evaluated_at = models.DateTimeField(auto_now_add=True)
        updated_at = models.DateTimeField(auto_now=True)

        class Meta:
            unique_together = ['student', 'subject']
            verbose_name = 'Student Subject Rating'
            verbose_name_plural = 'Student Subject Ratings'
            ordering = ['student__name', 'subject__name']

        def __str__(self):
            return f"{self.student.name} - {self.subject.get_name_display()}: {self.get_rating_display()}"

class Requirement(models.Model):
    SCHEDULE_STATUS_CHOICES = [
        ('not_scheduled', 'Not Scheduled'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled')
    ]

    company_name = models.CharField(max_length=100)
    company_code = models.CharField(max_length=20, blank=False, unique=True)
    requirement_date = models.DateField(null=True, blank=True)
    is_scheduled = models.BooleanField(default=False)
    schedule_date = models.DateField(null=True, blank=True)
    schedule_time = models.TimeField(null=True, blank=True)
    description = models.TextField(blank=True)
    schedule_status = models.CharField(
        max_length=20, 
        choices=SCHEDULE_STATUS_CHOICES,
        default='not_scheduled'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Escalation info
    escalation = models.TextField(blank=True, null=True, help_text="Details about the escalation raised")
    escalation_raised_at = models.DateTimeField(null=True, blank=True)

    # Many-to-many relationships
    students = models.ManyToManyField('Student', through='RequirementStudent')
    subjects = models.ManyToManyField('Subject', through='RequirementSubject')

    # New percentage fields
    percentage_10th = models.FloatField(null=True, blank=True, verbose_name="10th Percentage Criteria")
    percentage_12th = models.FloatField(null=True, blank=True, verbose_name="12th Percentage Criteria")
    percentage_degree = models.FloatField(null=True, blank=True, verbose_name="Degree Percentage Criteria")
    percentage_master = models.FloatField(null=True, blank=True, verbose_name="Master's Percentage Criteria")

    def __str__(self):
        return self.company_name

    def update_student_counts(self):
        for student in self.students.all():
            student.update_requirement_counts()

    @property
    def is_scheduled_today(self):
        return self.schedule_date == timezone.now().date()



# models.py
class RequirementSubject(models.Model):
    requirement = models.ForeignKey('Requirement', on_delete=models.CASCADE)
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    other_subject_name = models.CharField(max_length=100, blank=True, null=True)
    

    def __str__(self):
        if self.subject.name == 'other':
            return f"{self.requirement.company_code} - Other: {self.other_subject_name}"
        return f"{self.requirement.company_code} - {self.subject.get_name_display()}"


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
    total_requirements = models.IntegerField(default=0)
    scheduled_requirements = models.IntegerField(default=0)
    is_placed = models.BooleanField(default=False, verbose_name="Placed Status")
    
    # Dropout fields
    is_dropout = models.BooleanField(
        default=False,
        verbose_name="Dropout Status",
        help_text="Whether the student has dropped out or not"
    )
    dropout_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Dropout Date",
        help_text="Date when the student dropped out"
    )
    dropout_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Reason for Dropout",
        help_text="Explanation for why the student dropped out"
    )
    
    # Overall technical rating
    OVERALL_RATING_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('average', 'Average'),
        ('bad', 'Bad'),
    ]
    overall_technical_rating = models.CharField(
        max_length=20, 
        choices=OVERALL_RATING_CHOICES, 
        blank=True, 
        null=True,
        help_text="Overall technical rating based on subject ratings"
    )

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['gender']),
            models.Index(fields=['degree']),
            models.Index(fields=['is_dropout']),
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
    # Clean fields before saving
        if self.name:
            self.name = self.name.title()  # Proper case
        if self.degree:
            self.degree = self.degree.upper()  # All caps
        if self.stream:
            self.stream = self.stream.upper()  # All caps

    # Set dropout date if is_dropout is True and date isn't set
        if self.is_dropout and not self.dropout_date:
            self.dropout_date = timezone.now().date()

    # Clear dropout date if is_dropout is False
        if not self.is_dropout:
            self.dropout_date = None
            self.dropout_reason = None

    # Save the instance first to ensure it has a primary key
        super().save(*args, **kwargs)

    # Now it's safe to call this (after pk is available)
        self.update_overall_technical_rating()
    
    # Save again only if rating was changed
        Student.objects.filter(pk=self.pk).update(overall_technical_rating=self.overall_technical_rating)


    def update_overall_technical_rating(self):
        """Calculate overall technical rating based on subject ratings"""
        ratings = self.subject_ratings.all()
        if not ratings.exists():
            self.overall_technical_rating = None
            return
        
        # Count each rating type
        rating_counts = {
            'excellent': 0,
            'good': 0,
            'average': 0,
            'bad': 0
        }
        
        for rating in ratings:
            rating_counts[rating.rating] += 1
        
        total_ratings = len(ratings)
        
        # Determine overall rating based on majority
        if rating_counts['excellent'] / total_ratings >= 0.75:
            self.overall_technical_rating = 'excellent'
        elif rating_counts['good'] / total_ratings >= 0.5:
            self.overall_technical_rating = 'good'
        elif rating_counts['bad'] / total_ratings >= 0.5:
            self.overall_technical_rating = 'bad'
        else:
            self.overall_technical_rating = 'average'

    def update_requirement_counts(self):
        self.total_requirements = self.requirementstudent_set.count()
        self.scheduled_requirements = self.requirementstudent_set.filter(
            requirement__schedule_status='scheduled'
        ).count()
        self.save(update_fields=['total_requirements', 'scheduled_requirements'])

    def update_placement_status(self):
        # Don't update placement status if student is a dropout
        if self.is_dropout:
            return
            
        new_status = self.requirementstudent_set.filter(status='selected').exists() or hasattr(self, 'placed_outside')
        if self.is_placed != new_status:
            self.is_placed = new_status
            self.save(update_fields=['is_placed'])

    def get_subject_rating(self, subject_name):
        """Helper method to get a student's rating for a specific subject"""
        try:
            rating = self.subject_ratings.get(subject__name=subject_name)
            return rating.get_rating_display()
        except StudentSubjectRating.DoesNotExist:
            return "Not Rated"

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
    feedback = models.TextField(blank=True, null=True, verbose_name="Interview Feedback/Status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['student', 'requirement']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.requirement.company_name}"

    def save(self, *args, **kwargs):
        status_changed = False
        if self.pk:
            old_instance = RequirementStudent.objects.get(pk=self.pk)
            status_changed = (old_instance.status != self.status)

        super().save(*args, **kwargs)

        if status_changed or self.status == 'selected':
            self.student.update_placement_status()

    def check_auto_reject_status(self):
        if self.requirement.is_scheduled and self.requirement.schedule_date:
            expiration_time = self.requirement.schedule_date + timedelta(days=5)
            if timezone.now() > expiration_time and self.status == 'pending':
                self.status = 'rejected'
                self.save()
                return True
        return False
    
    @classmethod
    def get_monthly_summary(cls):
        return cls.objects.annotate(
            month=models.functions.TruncMonth('created_at')
        ).values('month').annotate(
            total=count('id'),
            scheduled=count('id', filter=models.Q(is_scheduled=True)),
            completed=count('id', filter=models.Q(schedule_status='completed'))
        ).order_by('-month')
    
    @classmethod
    def get_monthly_results(cls):
        return cls.objects.annotate(
            month=models.functions.TruncMonth('scheduled_date')
        ).values('month', 'result').annotate(
            count=count('id')
        ).order_by('-month')


class ScheduledRequirement(models.Model):
    RESULT_CHOICES = [
        ('pending', 'Result Pending'),
        ('selected', 'Got Selects'),
        ('no_selects', 'No Selects'),
        ('partial_scheduled', 'Partial Scheduled'),
        ('cancelled', 'Drive Cancelled'),
        ('postponed', 'Drive Postponed'),
    ]
    
    requirement = models.OneToOneField(
        Requirement,
        on_delete=models.CASCADE,
        related_name='scheduled_details'
    )
    scheduled_date = models.DateField()
    result = models.CharField(max_length=20, choices=RESULT_CHOICES, default='pending')
    feedback = models.TextField(blank=True, null=True)
    students_appeared = models.ManyToManyField(Student, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Scheduled details for {self.requirement}"

    class Meta:
        ordering = ['-scheduled_date']


class GotPlacedOutside(models.Model):
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='placed_outside')
    company_name = models.CharField(max_length=100, blank=True, null=True)
    package = models.CharField(max_length=50, blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, null=True)
    placed_date = models.DateField(default=timezone.now)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Set is_placed = True on the student
        self.student.is_placed = True
        self.student.save()

    def __str__(self):
        return f"{self.student.name} placed at {self.company_name}"


# Signal Handlers
@receiver(pre_save, sender=Requirement)
def track_schedule_status_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = Requirement.objects.get(pk=instance.pk)
            instance._old_status = old_instance.schedule_status
            instance._old_is_scheduled = old_instance.is_scheduled
        except Requirement.DoesNotExist:
            pass

@receiver(post_save, sender=Requirement)
def handle_scheduled_requirement(sender, instance, created, **kwargs):
    try:
        if instance.is_scheduled:
            # Get or create scheduled details if they don't exist
            ScheduledRequirement.objects.get_or_create(
                requirement=instance,
                defaults={'scheduled_date': instance.schedule_date or timezone.now().date()}
            )
        else:
            # Schedule cleanup for after transaction completes
            transaction.on_commit(
                lambda: cleanup_scheduled_requirement(instance)
            )
    except Exception as e:
        # Log the error if needed
        print(f"Error handling scheduled requirement: {str(e)}")

def cleanup_scheduled_requirement(requirement):
    """Clean up scheduled requirement after transaction completes"""
    try:
        if hasattr(requirement, 'scheduled_details'):
            requirement.scheduled_details.delete()
    except (ScheduledRequirement.DoesNotExist, AttributeError, ValueError):
        pass

@receiver(post_save, sender=Requirement)
def update_student_counts_on_schedule_change(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_old_status'):
        if instance._old_status != instance.schedule_status:
            transaction.on_commit(instance.update_student_counts)
        if hasattr(instance, '_old_is_scheduled') and instance._old_is_scheduled != instance.is_scheduled:
            transaction.on_commit(instance.update_student_counts)

@receiver(post_save, sender=RequirementStudent)
def handle_requirement_student_save(sender, instance, created, **kwargs):
    # Schedule updates for after transaction completes
    transaction.on_commit(instance.student.update_requirement_counts)
    transaction.on_commit(instance.student.update_placement_status)

@receiver(post_delete, sender=RequirementStudent)
def handle_requirement_student_delete(sender, instance, **kwargs):
    # Schedule updates for after transaction completes
    transaction.on_commit(instance.student.update_requirement_counts)
    transaction.on_commit(instance.student.update_placement_status)

@receiver(pre_save, sender=ScheduledRequirement)
def track_result_change(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = ScheduledRequirement.objects.get(pk=instance.pk)
            instance._old_result = old_instance.result
        except ScheduledRequirement.DoesNotExist:
            pass

@receiver(post_save, sender=ScheduledRequirement)
def update_requirement_status_from_result(sender, instance, created, **kwargs):
    if not created and hasattr(instance, '_old_result') and instance._old_result != instance.result:
        def update_status():
            requirement = Requirement.objects.get(pk=instance.requirement_id)
            if instance.result in ['selected', 'no_selects', 'partial_scheduled']:
                requirement.schedule_status = 'completed'
            elif instance.result in ['cancelled', 'postponed']:
                requirement.schedule_status = 'cancelled'
            requirement.save()
        
        transaction.on_commit(update_status)

@receiver(post_delete, sender=ScheduledRequirement)
def handle_scheduled_requirement_delete(sender, instance, **kwargs):
    def cleanup_requirement():
        requirement = Requirement.objects.get(pk=instance.requirement_id)
        requirement.is_scheduled = False
        requirement.schedule_status = 'not_scheduled'
        requirement.save()
    
    transaction.on_commit(cleanup_requirement)

@receiver(post_save, sender=StudentSubjectRating)
@receiver(post_delete, sender=StudentSubjectRating)
def update_student_overall_rating(sender, instance, **kwargs):
    """Update the student's overall technical rating when subject ratings change"""
    transaction.on_commit(instance.student.save)