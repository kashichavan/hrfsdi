from django.contrib import admin
from .models import RequirementStudent, RequirementSubject

class RequirementStudentInline(admin.TabularInline):
    model = RequirementStudent
    extra = 0
    autocomplete_fields = ['student']
    fields = ['student', 'status', 'remarks']
    readonly_fields = []
    show_change_link = True
    verbose_name = "Assigned Student"
    verbose_name_plural = "Assigned Students"

class ScheduledRequirementInline(admin.TabularInline):
    model = RequirementSubject
    extra = 0
    autocomplete_fields = ['subject']
    fields = ['subject', 'other_subject_name']
    show_change_link = False
    verbose_name = "Scheduled Subject"
    verbose_name_plural = "Scheduled Subjects"
