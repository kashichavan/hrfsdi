from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Student, Requirement, RequirementStudent
from django.core.files.uploadedfile import SimpleUploadedFile
import pandas as pd
import io

class StudentDataViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password')
        self.client.login(username='testuser', password='password')

        # Create sample data
        self.student1 = Student.objects.create(
            name='John Doe', contact_number='1234567890', degree='B.Tech', stream='CSE',
            yop=2023, tenth_percent=90.0, twelfth_percent=85.0, degree_percent=80.0,
            gender='Male', type_of_data='FSDI'
        )
        self.student2 = Student.objects.create(
            name='Jane Smith', contact_number='9876543210', degree='B.Tech', stream='ECE',
            yop=2022, tenth_percent=95.0, twelfth_percent=92.0, degree_percent=88.0,
            gender='Female', type_of_data='Super100'
        )
        self.requirement = Requirement.objects.create(
            company_name='Acme Corp', company_code='AC123', is_scheduled=False
        )

    def test_upload_excel_get(self):
        response = self.client.get(reverse('upload_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'upload.html')

    def test_upload_excel_post_valid(self):
        # Create a dummy Excel file
        data = {'name': ['Test Student'], 'contact_number': ['1122334455'],
                'degree': ['B.Tech'], 'stream': ['CSE'], 'yop': [2024],
                'tenth_percent': [80], 'twelfth_percent': [85],
                'degree_percent': [90], 'gender': ['Male'], 'type_of_data': ['FSDI']}
        df = pd.DataFrame(data)
        excel_file = io.BytesIO()
        df.to_excel(excel_file, index=False, engine='openpyxl')
        excel_file.seek(0)
        uploaded_file = SimpleUploadedFile("test.xlsx", excel_file.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        response = self.client.post(reverse('upload_excel'), {'excel_file': uploaded_file})
        self.assertEqual(response.status_code, 302)  # Expect a redirect
        self.assertRedirects(response, reverse('processing_page'))
        # Add more assertions to check if the task is created and processed

    def test_upload_excel_post_invalid_file_type(self):
        # Create a dummy text file
        text_file = SimpleUploadedFile("test.txt", b"file_content", content_type="text/plain")
        response = self.client.post(reverse('upload_excel'), {'excel_file': text_file})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'upload.html')
        self.assertIn('error', response.context)

    def test_processing_page_get(self):
        # Simulate a task ID in the session
        session = self.client.session
        session['excel_task_id'] = 'test_task_id'
        session.save()

        response = self.client.get(reverse('processing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'processing.html')
        self.assertEqual(response.context['task_id'], 'test_task_id')

    def test_check_task_status_get(self):
        # This test requires mocking the cache, which is beyond the scope of this initial setup.
        pass

    def test_student_list_get(self):
        response = self.client.get(reverse('student_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'studentlist.html')
        self.assertIn('page_obj', response.context)

    def test_student_detail_get(self):
        response = self.client.get(reverse('student_detail', args=[self.student1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'student_detail.html')
        self.assertIn('student', response.context)

    def test_requirement_list_get(self):
        response = self.client.get(reverse('requirement_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirement_list.html')
        self.assertIn('page_obj', response.context)

    def test_add_requirement_get(self):
        response = self.client.get(reverse('add_requirement'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_requirement.html')
        self.assertIn('form', response.context)

    def test_add_requirement_post_valid(self):
        # Simulate form submission with valid data
        data = {
            'company_name': 'New Company',
            'company_code': 'NC001',
        }
        response = self.client.post(reverse('add_requirement'), data)
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the requirement is created and redirects correctly

    def test_requirement_detail_get(self):
        response = self.client.get(reverse('requirement_detail', args=[self.requirement.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirement_detail.html')
        self.assertIn('requirement', response.context)

    def test_requirement_edit_get(self):
        response = self.client.get(reverse('requirement_edit', args=[self.requirement.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirement_edit.html')
        self.assertIn('form', response.context)

    def test_requirement_edit_post_valid(self):
        data = {
            'company_name': 'Updated Company Name',
            'company_code': 'AC123',
            'is_scheduled': True,
        }
        response = self.client.post(reverse('requirement_edit', args=[self.requirement.id]), data)
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the requirement is updated and redirects correctly

    def test_requirement_students_get(self):
        response = self.client.get(reverse('requirement_students', args=[self.requirement.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'requirement_students.html')
        self.assertIn('requirement', response.context)

    def test_update_student_status_post(self):
        # Create a RequirementStudent instance
        RequirementStudent.objects.create(student=self.student1, requirement=self.requirement, status='pending')
        response = self.client.post(
            reverse('update_student_status', args=[self.requirement.id, self.student1.id]),
            {'status': 'selected'}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the status is updated

    def test_bulk_import_students_post(self):
        # This test requires creating a dummy Excel file and is similar to test_upload_excel_post_valid
        pass

    def test_remove_requirement_student_post(self):
        # Create a RequirementStudent instance
        req_student = RequirementStudent.objects.create(student=self.student1, requirement=self.requirement)
        response = self.client.get(reverse('remove_requirement_student', args=[self.requirement.id, self.student1.id]))
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the student is removed

    def test_bulk_remove_requirement_students_post(self):
        # Create RequirementStudent instances
        RequirementStudent.objects.create(student=self.student1, requirement=self.requirement)
        RequirementStudent.objects.create(student=self.student2, requirement=self.requirement)

        response = self.client.post(
            reverse('bulk_remove_requirement_students', args=[self.requirement.id]),
            {'student_ids': [self.student1.id, self.student2.id]}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if students are removed

    def test_add_students_to_requirement_post(self):
        response = self.client.post(
            reverse('add_students_to_requirement', args=[self.requirement.id]),
            {'student_ids': [self.student1.id, self.student2.id]}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if students are added

    def test_update_student_status_view_post(self):
        # This test is for the 'update_student_status' view (different URL name)
        RequirementStudent.objects.create(student=self.student1, requirement=self.requirement, status='pending')
        response = self.client.post(
            reverse('requirements:update_student_status', args=[self.requirement.id, self.student1.id]),
            {'status': 'selected'}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the status is updated

    def test_remove_student_from_requirement_post(self):
        # This test is for the 'remove_student_from_requirement' view (different URL name)
        RequirementStudent.objects.create(student=self.student1, requirement=self.requirement)
        response = self.client.get(reverse('requirements:remove_student_from_requirement', args=[self.requirement.id, self.student1.id]))
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the student is removed

    def test_bulk_remove_students_post(self):
        # This test is for the 'bulk_remove_students' view (different URL name)
        RequirementStudent.objects.create(student=self.student1, requirement=self.requirement)
        RequirementStudent.objects.create(student=self.student2, requirement=self.requirement)

        response = self.client.post(
            reverse('requirements:bulk_remove_students', args=[self.requirement.id]),
            {'student_ids': [self.student1.id, self.student2.id]}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if students are removed

    def test_update_requirement_schedule_post(self):
        response = self.client.post(
            reverse('update_requirement_schedule', args=[self.requirement.id]),
            {'schedule_status': 'scheduled'}
        )
        self.assertEqual(response.status_code, 302)
        # Add assertions to check if the schedule status is updated

    def test_home_dashboard_get(self):
        response = self.client.get(reverse('home_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home_dashboard.html')
        self.assertIn('total_students', response.context)

    def test_student_analytics_get(self):
        response = self.client.get(reverse('student_analytics'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/student_analytics.html')
        self.assertIn('charts', response.context)

    def test_performance_trends_get(self):
        response = self.client.get(reverse('performance_trends'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'analytics/performance_trends.html')
        self.assertIn('performance_dashboard', response.context)
