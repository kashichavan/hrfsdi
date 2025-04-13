# urls.py
from django.urls import path
from . import views
from .apps import StudentDataConfig
app_name = StudentDataConfig.name

urlpatterns = [
    # Dashboard URLs
    path('', views.home_dashboard, name='home_dashboard'),
    
    # Student Management URLs
    path('students/', views.student_list, name='student_list'),
    path('students/<int:student_id>/', views.student_detail, name='student_detail'),
    
    # Excel Upload URLs
    path('upload/', views.upload_excel, name='upload_excel'),
    path('processing/', views.processing_page, name='processing_page'),
    path('check-task-status/', views.check_task_status, name='check_task_status'),
    
    # Requirement Management URLs
    path('requirements/', views.requirement_list, name='requirement_list'),
    path('requirements/add/', views.add_requirement, name='add_requirement'),
    path('requirements/<int:pk>/', views.requirement_detail, name='requirement_detail'),
    path('requirements/<int:pk>/edit/', views.requirement_edit, name='requirement_edit'),
    
    # Requirement Student Management URLs
    path('requirements/<int:pk>/students/', views.requirement_students, name='requirement_students'),
    path('requirements/<int:requirement_id>/students/<int:student_id>/update-status/',
         views.update_student_status, name='update_student_status'),
    path('requirements/<int:requirement_id>/bulk-import/',
         views.bulk_import_students, name='bulk_import_students'),
    
    # Remove Students from Requirements
    path('requirements/<int:requirement_id>/students/<int:student_id>/remove/',
         views.remove_requirement_student, name='remove_requirement_student'),
    path('requirements/<int:requirement_id>/bulk-remove/',
         views.bulk_remove_requirement_students, name='bulk_remove_requirement_students'),
    
    # Add Students to Requirements
    path('requirements/<int:requirement_id>/add-students/',
         views.add_students_to_requirement, name='add_students_to_requirement'),
    
    # Update Requirement Schedule
    path('requirements/<int:requirement_id>/update-schedule/',
         views.update_requirement_schedule, name='update_requirement_schedule'),

      path('analytics/', views.student_analytics, name='student_analytics'),
]