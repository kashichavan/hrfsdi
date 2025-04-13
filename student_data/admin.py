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
