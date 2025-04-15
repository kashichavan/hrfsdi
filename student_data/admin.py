from django.contrib import admin

# Register your models here.
# admin.py
from django.contrib import admin
from .models import Student

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'degree', 'stream', 'yop', 'gender')
    search_fields = ('name', 'contact_number', 'degree')
    list_filter = ('gender', 'degree', 'stream', 'type_of_data')
    list_per_page = 50  # For better admin performance with large datasets

from django.contrib import admin
from .models import Requirement, RequirementStudent

@admin.register(Requirement)
class RequirementAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'company_code',
        'requirement_date',
        'schedule_status',
        'is_scheduled',
        'schedule_date',
        'schedule_time',
        'created_at',
    )
    
    search_fields = (
        'company_name',
        'company_code',
        'description',
    )
    
    list_filter = (
        'schedule_status',
        'is_scheduled',
        'requirement_date',
        'schedule_date',
    )
    
    list_editable = (
        'schedule_status',
        'is_scheduled',
    )
    
    fieldsets = (
        ('Company Information', {
            'fields': ('company_name', 'company_code', 'description')
        }),
        ('Scheduling Information', {
            'fields': (
                'requirement_date',
                'is_scheduled',
                'schedule_date',
                'schedule_time',
                'schedule_status',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'schedule_date'
    list_per_page = 25
    save_on_top = True
    
    def is_scheduled_today_display(self, obj):
        return obj.is_scheduled_today
    is_scheduled_today_display.boolean = True
    is_scheduled_today_display.short_description = 'Scheduled Today?'

@admin.register(RequirementStudent)
class RequirementStudentAdmin(admin.ModelAdmin):
    list_display = (
        'student',
        'requirement',
        'status',
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'requirement__company_name')
    search_fields = (
        'student__name',
        'requirement__company_name',
    )
    raw_id_fields = ('student', 'requirement')
    list_editable = ('status',)
    list_per_page = 50