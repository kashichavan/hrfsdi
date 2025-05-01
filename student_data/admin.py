from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Student, Subject, StudentSubjectRating, 
    Requirement, RequirementStudent,
    ScheduledRequirement, GotPlacedOutside
)
from .forms import *

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_name_display', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    ordering = ('name',)
    actions = ['activate_subjects', 'deactivate_subjects']

    def activate_subjects(self, request, queryset):
        queryset.update(is_active=True)
    activate_subjects.short_description = "Activate selected subjects"

    def deactivate_subjects(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_subjects.short_description = "Deactivate selected subjects"


class StudentSubjectRatingInline(admin.TabularInline):
    model = StudentSubjectRating
    extra = 1
    fields = ('subject', 'rating', 'remarks', 'evaluated_by', 'evaluated_at')
    readonly_fields = ('evaluated_at',)
    autocomplete_fields = ('subject',)

from .models import *
class RequirementSubjectInline(admin.TabularInline):
    model = RequirementSubject
    extra = 1
    autocomplete_fields = ['subject']  # Allow autocomplete for subjects
    fk_name = 'requirement'  # Link to the Requirement model

class RequirementStudentInline(admin.TabularInline):
    model = RequirementStudent
    extra = 1
    fields = ('student', 'status', 'feedback', 'created_at')
    readonly_fields = ('created_at',)
    raw_id_fields = ('student',)
    show_change_link = True

class ScheduledRequirementInline(admin.StackedInline):
    model = ScheduledRequirement
    extra = 0
    min_num = 0
    max_num = 1
    fields = ('scheduled_date', 'result', 'feedback', 'students_appeared')
    filter_horizontal = ('students_appeared',)
    can_delete = False

@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        'company_name', 
        'company_code', 
        'schedule_status', 
        'schedule_date',
        'is_scheduled_today',
        'created_at'
    )
    list_filter = (
        'schedule_status',
        'is_scheduled',
        ('schedule_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'company_name', 
        'company_code',
        'description'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'company_name',
                'company_code',
                'description'
            )
        }),
        ('Scheduling Information', {
            'fields': (
                'requirement_date',
                'is_scheduled',
                'schedule_status',
                'schedule_date',
                'schedule_time',
            )
        }),
        ('Escalation', {
            'fields': (
                'escalation',
                'escalation_raised_at',
            ),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ScheduledRequirementInline, RequirementStudentInline]
    date_hierarchy = 'schedule_date'
    ordering = ('-created_at',)
    actions = ['mark_as_completed', 'mark_as_cancelled']

    def mark_as_completed(self, request, queryset):
        queryset.update(schedule_status='completed')
    mark_as_completed.short_description = "Mark selected requirements as completed"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(schedule_status='cancelled')
    mark_as_cancelled.short_description = "Mark selected requirements as cancelled"

    def is_scheduled_today(self, obj):
        return obj.is_scheduled_today
    is_scheduled_today.boolean = True
    is_scheduled_today.short_description = 'Today?'

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'degree',
        'stream',
        'yop',
        'degree_percent',
        'total_requirements',
        'scheduled_requirements',
        'is_placed',
        'created_at'
    )
    list_filter = (
        'degree',
        'stream',
        'yop',
        'gender',
        'is_placed'
    )
    search_fields = (
        'name',
        'contact_number',
        'degree',
        'stream'
    )
    fieldsets = (
        ('Personal Information', {
            'fields': (
                'name',
                'contact_number',
                'gender',
                'type_of_data'
            )
        }),
        ('Academic Information', {
            'fields': (
                'degree',
                'stream',
                'yop',
                'tenth_percent',
                'twelfth_percent',
                'degree_percent'
            )
        }),
        ('Placement Information', {
            'fields': (
                'total_requirements',
                'scheduled_requirements',
                'is_placed'
            )
        }),
    )
    readonly_fields = (
        'total_requirements',
        'scheduled_requirements',
        'created_at'
    )
    list_per_page = 50
    ordering = ('-created_at',)

@admin.register(RequirementStudent)
class RequirementStudentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'requirement',
        'status',
        'created_at',
        'updated_at'
    )
    list_filter = (
        'status',
        'requirement__company_name',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'student__name',
        'requirement__company_name',
        'feedback'
    )
    raw_id_fields = ('student', 'requirement')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_select_related = ('student', 'requirement')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('student', 'requirement')

@admin.register(ScheduledRequirement)
class ScheduledRequirementAdmin(admin.ModelAdmin):
    list_display = (
        'requirement',
        'scheduled_date',
        'result',
        'students_appeared_count',
        'created_at'
    )
    list_filter = (
        'result',
        ('scheduled_date', admin.DateFieldListFilter),
    )
    search_fields = (
        'requirement__company_name',
        'feedback'
    )
    filter_horizontal = ('students_appeared',)
    raw_id_fields = ('requirement',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_date'

    def students_appeared_count(self, obj):
        return obj.students_appeared.count()
    students_appeared_count.short_description = 'Students Appeared'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('requirement')
    

class ScheduledRequirementInline(admin.StackedInline):
    model = ScheduledRequirement
    extra = 0
    min_num = 0
    max_num = 1
    fields = ('scheduled_date', 'result', 'feedback', 'students_appeared')
    filter_horizontal = ('students_appeared',)
    can_delete = False
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['scheduled_date'].required = False
        return formset