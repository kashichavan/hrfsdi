# urls.py
from django.urls import path
from . import views


app_name='student_data'

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

    
    # Update Requirement Schedule
    path('requirements/<int:requirement_id>/update-schedule/',
         views.update_student_status, name='update_requirement_schedule'),

     path('analytics/', views.student_analytics, name='student_analytics'),
     path('performance/',views.performance_trends,name='performance'),

      # urls.py
path('requirements/<int:requirement_id>/', 
     views.add_students_to_requirement, 
     name='add_students_to_requirement'),

     path('assign-students/<int:requirement_id>/', views.add_students_to_requirement, name='add-student-to-requirement'),
     path('todays-requirements/', views.todays_requirements_view, name='todays_requirements'),
     path('students-attending-today/', views.students_attending_today, name='students_attending_today'),
     path('export/todays-requirements/', views.export_today_scheduled_requirements, name='export_todays_requirements'),
     path('requirement/<int:requirement_id>/student/<int:student_id>/remove/', views.remove_student_from_requirement, name='remove_student'),
     path('student/delete/<int:pk>/',views.StudentDeleteView.as_view(), name='student_delete'),
     path('requirements/delete_all/', views.delete_all_requirements, name='delete_all_requirements'),
     # hidden
     path('upload-requirements/', views.upload_requirements_view, name='upload_requirements'),
     path('map-students/', views.map_students_to_requirement_view, name='map_students'),
     #path('placement/update-status/', views.update_selected_students, name='update_selected_students'),
    

    path('add/', views.add_student, name='add_student'),
     path('update-status/', views.combined_view, name='update_status'),
     path('placed/',views.placed_students_view,name='placed_students'),
      path('requirements/<int:pk>/delete/', views.delete_requirement, name='delete_requirement'),
]