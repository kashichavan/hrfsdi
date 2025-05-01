from django.contrib import admin
from .models import (
    Requirement,
    RequirementSubject,
    Subject,
    Student,
    RequirementStudent,
    StudentSubjectRating,
    GotPlacedOutside
)


class RequirementSubjectInline(admin.TabularInline):
    model = RequirementSubject
    extra = 1
    autocomplete_fields = ['subject']
    fields = (
        'subject', 'other_subject_name'
    )


class RequirementStudentInline(admin.TabularInline):
    model = RequirementStudent
    extra = 1
    autocomplete_fields = ['student']


@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        'company_name', 'company_code', 'requirement_date',
        'schedule_date', 'schedule_status', 'is_scheduled',
        'percentage_10th', 'percentage_12th', 'percentage_degree', 'percentage_master',
    )
    list_filter = ('schedule_status', 'is_scheduled', 'schedule_date')
    search_fields = ('company_name', 'company_code')
    ordering = ('-schedule_date',)
    date_hierarchy = 'schedule_date'
    inlines = [RequirementSubjectInline, RequirementStudentInline]  # Inlines handle the relationship

    fieldsets = (
        ('Company Info', {
            'fields': ('company_name', 'company_code', 'description')
        }),
        ('Schedule Details', {
            'fields': ('requirement_date', 'is_scheduled', 'schedule_date', 'schedule_time', 'schedule_status')
        }),
        ('Escalation (Optional)', {
            'classes': ('collapse',),
            'fields': ('escalation', 'escalation_raised_at')
        }),
        ('Percentage Criteria', {
            'fields': ('percentage_10th', 'percentage_12th', 'percentage_degree', 'percentage_master'),
            'description': 'Enter the percentage values for 10th, 12th, Degree, and Master\'s if applicable.',
        }),
        
        
        # Removed subjects field and the ManyToMany field from filter_horizontal/filter_vertical
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)
    list_filter = ('is_active',)


@admin.register(RequirementSubject)
class RequirementSubjectAdmin(admin.ModelAdmin):
    list_display = (
        'requirement', 'subject', 'other_subject_name',)
    search_fields = ('requirement__company_code', 'subject__name', 'other_subject_name')


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_number', 'degree', 'stream', 'yop', 'is_placed')
    search_fields = ('name', 'contact_number', 'stream')
    list_filter = ('degree', 'stream', 'yop', 'is_placed')


@admin.register(StudentSubjectRating)
class StudentSubjectRatingAdmin(admin.ModelAdmin):
    list_display = ('student', 'subject', 'rating', 'evaluated_by')
    search_fields = ('student__name', 'subject__name', 'evaluated_by')
    list_filter = ('rating',)


@admin.register(GotPlacedOutside)
class GotPlacedOutsideAdmin(admin.ModelAdmin):
    list_display = ('student', 'company_name', 'role', 'package', 'placed_date')
    search_fields = ('student__name', 'company_name', 'role')
    list_filter = ('placed_date',)
