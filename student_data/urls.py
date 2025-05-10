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
    path('student/delete/<int:pk>/', views.StudentDeleteView.as_view(), name='student_delete'),
    path('add/', views.StudentCreateView.as_view(), name='add'),
    
    # Excel Upload URLs
    path('upload/', views.upload_excel, name='upload_excel'),
    path('processing/', views.processing_page, name='processing_page'),
    path('check-task-status/', views.check_task_status, name='check_task_status'),
    
    # Requirement Management URLs
    path('requirements/', views.requirement_list, name='requirement_list'),
    path('requirements/add/', views.add_requirement, name='add_requirement'),
    path('requirements/<int:pk>/', views.requirement_detail, name='requirement_detail'),
    path('requirements/<int:pk>/edit/', views.requirement_edit, name='requirement_edit'),
    path('requirements/<int:pk>/delete/', views.delete_requirement, name='delete_requirement'),
    path('requirements/delete_all/', views.delete_all_requirements, name='delete_all_requirements'),
    
    # Requirement Student Management URLs
    path('requirements/<int:pk>/students/', views.requirement_students, name='requirement_students'),
    path('requirements/<int:requirement_id>/students/<int:student_id>/update-status/',
         views.update_student_status, name='update_student_status'),
    path('requirements/<int:requirement_id>/bulk-import/',
         views.bulk_import_students, name='bulk_import_students'),
    path('requirements/<int:requirement_id>/', 
         views.add_students_to_requirement, 
         name='add_students_to_requirement'),
    path('assign-students/<int:requirement_id>/', 
         views.add_students_to_requirement, 
         name='add-student-to-requirement'),
    
    # Remove Students from Requirements
    path('requirements/<int:requirement_id>/students/<int:student_id>/remove/',
         views.remove_requirement_student, name='remove_requirement_student'),
    path('requirement/<int:requirement_id>/student/<int:student_id>/remove/', 
         views.remove_student_from_requirement, name='remove_student'),
    path('requirements/<int:requirement_id>/bulk-remove/',
         views.bulk_remove_requirement_students, name='bulk_remove_requirement_students'),

    # Update Requirement Schedule
    path('requirements/<int:requirement_id>/update-schedule/',
         views.update_requirement_schedule, name='update_requirement_schedule'),
    
    # Analytics and Performance URLs
    path('analytics/', views.student_analytics, name='student_analytics'),
    path('performance/', views.performance_trends, name='performance'),
    
    # Today's Requirements URLs
    path('todays-requirements/', views.todays_requirements_view, name='todays_requirements'),
    path('students-attending-today/', views.students_attending_today, name='students_attending_today'),
    path('export/todays-requirements/', views.export_today_scheduled_requirements, name='export_todays_requirements'),
    
    # Hidden/Admin URLs
    path('upload-requirements/', views.upload_requirements_view, name='upload_requirements'),
    path('map-students/', views.map_students_to_requirement_view, name='map_students'),
    
    # Placement URLs
    path('placement/update-status/', views.update_selected_students, name='update_selected_students'),
    path('placed/', views.placed_students_view, name='placed_students'),
    path('update-status/', views.combined_view, name='update_status'),
    
    # Template Downloads
    path('download-template/', views.download_template, name='download_template'),
    path('download-template1/', views.download_student_selection_template, name='download_selected_students_template'),
    path('download-template2/', views.download_excel_template, name='download_excel_template'),
    path('download-sample/', views.download_sample_excel, name='download_sample'),
    
    # Feedback URLs
    path('update_student_feedback/<int:requirement_id>/', views.update_student_feedback, name='update_student_feedback'),
    
    # Escalation URLs
    path('requirement/<int:pk>/raise-escalation/', views.RaiseEscalationView.as_view(), name='raise_escalation'),

     
    #path('monthly-summary/companies/', views.add_sr, name='monthly_companies_data'),
     path('reports/monthly/', views.MonthlyReportsView.as_view(), name='monthly_reports'),
     path('students/edit/<int:pk>/', views.StudentUpdateView.as_view(), name='student_edit'),
     path('requirements/<int:pk>/update-drive-result/', views.update_drive_result, name='update_drive_result'),
     path('got-placed-outside/add/', views.add_got_placed_student, name='add_got_placed_outside'),
     path('bulk-outside-placement/', views.BulkOutsidePlacementView.as_view(), name='bulk_outside_placement'),
     path('requirement/<int:pk>/export/', views.export_requirement_students_excel, name='export_requirement_students_excel'),
     path('placed-outside/', views.students_placed_outside, name='placed_outside'),
     path('monthly-reports/download-excel/', views.ExportHRReportExcelView.as_view(), name='export_hr_excel'),
     path('update-escalation/<int:pk>/', views.update_escalation, name='update_escalation'),
     path('mark_as_scheduled/', views.mark_as_scheduled, name='mark_as_scheduled'),
       
     path('students/<int:student_id>/update-subject-ratings/', 
         views.StudentSubjectRatingsUpdateView.as_view(), 
         name='update-student-subject-ratings'),
        
     path('bulk-rating-upload/', views.BulkStudentRatingUploadView.as_view(), name='bulk_rating_upload'),
      path('download-rating-template/', views.DownloadRatingTemplateView.as_view(), name='download_rating_template'),
     path('students/<int:pk>/add-rating/', views.add_subject_rating, name='add_subject_rating'),
     path('student/<int:pk>/subject-rating/<int:rating_id>/', views.add_subject_rating, name='add_subject_rating'),
     path('bulk-add-dropouts/', views.bulk_add_dropouts, name='bulk_add_dropouts'),



     # TOMORROW
     path('tomorrow-requirements/', views.tomorrows_requirements, name='tomorrow_requirements'),
     path('tomorrow-students/', views.students_attending_tomorrow, name='tomorrow_students'),
     path('export/tomorrow-requirements/', views.export_tomorrow_scheduled_requirements, name='export_tomorrows_requirements'),
     path('student/<int:student_id>/placement/', views.update_placement_status, name='update_placement'),
     path('students/<int:student_id>/remove-placement/',views.remove_placement,name='remove_placement'),
     path('map_download-sample/', views.download_sample_excel_map, name='map_download_sample'),
     path('ajax/search-students/', views.ajax_search_students, name='ajax_search_students'),
    path('export/students-csv/', views.export_students_csv, name='export_students_csv'),

 path('ajax/today-requirements/', views.TodaysRequirementsAjaxView.as_view(), name='ajax_todays_requirements'),
    path('ajax/tomorrow-requirements/', views.TomorrowsRequirementsAjaxView.as_view(), name='ajax_tomorrow_requirements'),
    path('ajax/today-students/', views.TodaysStudentsAjaxView.as_view(), name='ajax_today_students'),
    path('ajax/tomorrow-students/', views.TomorrowsStudentsAjaxView.as_view(), name='ajax_tomorrow_students'),
]



