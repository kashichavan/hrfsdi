from django.shortcuts import render, redirect
from django.db import transaction
from django.http import JsonResponse
from .models import Student
import pandas as pd
import re
import threading
import uuid
import json
import os
from django.core.cache import cache
from django.conf import settings

def normalize_column_name(name):
    name = str(name).strip().lower()
    name = re.sub(r'\s+', '_', name)
    name = name.replace('%', '_percent')
    name = name.replace('10th', 'tenth')
    name = name.replace('12th', 'twelfth')
    return name

def process_excel_data(file_path, task_id):
    try:
        cache.set(f'task_{task_id}_status', json.dumps({
            'status': 'processing',
            'progress': 0,
            'message': 'Starting processing...'
        }), timeout=3600)

        df = pd.read_excel(file_path)

        if df.empty:
            raise ValueError("Uploaded file is empty.")

        df.columns = [normalize_column_name(col) for col in df.columns]
        df = df.drop(columns=['sl_no'], errors='ignore')

        required_columns = {
            'name', 'contact_number', 'degree', 'stream',
            'yop', 'tenth_percent', 'twelfth_percent',
            'degree_percent', 'gender', 'type_of_data'
        }
        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns: {', '.join(missing)}")

        df['yop'] = pd.to_numeric(df['yop'], errors='coerce').fillna(0).astype(int)
        numeric_cols = ['tenth_percent', 'twelfth_percent', 'degree_percent']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

        # Drop duplicates based on contact_number, keeping the first occurrence
        df = df.drop_duplicates(subset=['contact_number'], keep='first')
        
        total_rows = len(df)
        chunk_size = 1000
        processed_rows = 0
        duplicates_count = 0

        with transaction.atomic():
            for start in range(0, total_rows, chunk_size):
                end = min(start + chunk_size, total_rows)
                chunk_df = df.iloc[start:end]
                
                # Process each row to handle existing records
                for _, row in chunk_df.iterrows():
                    if pd.isna(row.get('name', '')) or pd.isna(row.get('contact_number', '')):
                        continue
                        
                    contact_number = row.get('contact_number', '')
                    
                    # Try to get existing student with this contact number
                    try:
                        existing_student = Student.objects.get(contact_number=contact_number)
                        
                        # Update existing student
                        existing_student.name = row.get('name', '')
                        existing_student.degree = row.get('degree', '')
                        existing_student.stream = row.get('stream', '')
                        existing_student.yop = row.get('yop', 0)
                        existing_student.tenth_percent = row.get('tenth_percent', 0.0)
                        existing_student.twelfth_percent = row.get('twelfth_percent', 0.0)
                        existing_student.degree_percent = row.get('degree_percent', 0.0)
                        existing_student.gender = row.get('gender', 'Male')
                        existing_student.type_of_data = row.get('type_of_data', '')
                        existing_student.save()
                        duplicates_count += 1
                    except Student.DoesNotExist:
                        # Create new student
                        Student.objects.create(
                            name=row.get('name', ''),
                            contact_number=contact_number,
                            degree=row.get('degree', ''),
                            stream=row.get('stream', ''),
                            yop=row.get('yop', 0),
                            tenth_percent=row.get('tenth_percent', 0.0),
                            twelfth_percent=row.get('twelfth_percent', 0.0),
                            degree_percent=row.get('degree_percent', 0.0),
                            gender=row.get('gender', 'Male'),
                            type_of_data=row.get('type_of_data', '')
                        )

                processed_rows += len(chunk_df)
                progress = min(int((processed_rows / total_rows) * 100), 95)
                cache.set(f'task_{task_id}_status', json.dumps({
                    'status': 'processing',
                    'progress': progress,
                    'message': f'Processed {processed_rows} / {total_rows} rows. Updated {duplicates_count} existing records.'
                }), timeout=3600)

        cache.set(f'task_{task_id}_status', json.dumps({
            'status': 'completed',
            'progress': 100,
            'message': f'Successfully processed {processed_rows} records. Updated {duplicates_count} existing records.'
        }), timeout=3600)

    except Exception as e:
        cache.set(f'task_{task_id}_status', json.dumps({
            'status': 'error',
            'message': str(e)
        }), timeout=3600)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def upload_excel(request):
    if request.method == 'POST':
        excel_file = request.FILES.get('excel_file')

        if not excel_file or not excel_file.name.endswith(('.xlsx', '.xls')):
            return render(request, 'upload.html', {'error': 'Invalid file format'})

        try:
            temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_excel')
            os.makedirs(temp_dir, exist_ok=True)

            unique_filename = f"{uuid.uuid4().hex}_{excel_file.name}"
            file_path = os.path.join(temp_dir, unique_filename)

            with open(file_path, 'wb+') as destination:
                for chunk in excel_file.chunks():
                    destination.write(chunk)

            task_id = str(uuid.uuid4())

            cache.set(f'task_{task_id}_status', json.dumps({
                'status': 'pending',
                'progress': 0,
                'message': 'Task pending...'
            }), timeout=3600)

            threading.Thread(
                target=process_excel_data,
                args=(file_path, task_id),
                daemon=True
            ).start()

            request.session['excel_task_id'] = task_id
            return redirect('processing_page')

        except Exception as e:
            return render(request, 'upload.html', {'error': f"Error processing file: {str(e)}"})

    return render(request, 'upload.html')

def processing_page(request):
    task_id = request.session.get('excel_task_id')
    if not task_id:
        return redirect('upload_excel')
    return render(request, 'processing.html', {'task_id': task_id})

def check_task_status(request):
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({'status': 'error', 'message': 'No task ID provided'})

    status_data = cache.get(f'task_{task_id}_status')
    if not status_data:
        return JsonResponse({'status': 'error', 'message': 'Task not found or expired'})

    try:
        status = json.loads(status_data)
        return JsonResponse(status)
    except:  # Fixed error: removed unexpected 'x' character
        return JsonResponse({'status': 'error', 'message': 'Invalid task status data'})
    


    # views.py (add these functions)
from django.core.paginator import Paginator
from django.db.models import Q

from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.shortcuts import render

from django.shortcuts import render
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import Student

def student_list(request):
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', 'name')
    page_number = request.GET.get('page', 1)
    type_filter = request.GET.get('type_filter', '')

    degree_filter = request.GET.get('degree', '')
    stream_filters = request.GET.getlist('stream')
    min_tenth = request.GET.get('min_tenth', '')
    min_twelfth = request.GET.get('min_twelfth', '')
    min_degree = request.GET.get('min_degree', '')
    gender_filter = request.GET.get('gender', '')
    min_yop = request.GET.get('min_yop', '')
    max_yop = request.GET.get('max_yop', '')

    # Annotate with counts
    students = Student.objects.annotate(
        total_requirements_count=Count('requirementstudent'),
        scheduled_requirements_count=Count(
            'requirementstudent',
            filter=Q(requirementstudent__requirement__is_scheduled=True)
        )
    )

    if type_filter:
        students = students.filter(type_of_data__iexact=type_filter.lower())

    if degree_filter:
        students = students.filter(degree__icontains=degree_filter)

    if stream_filters:
        stream_query = Q()
        for stream in stream_filters:
            if stream:
                stream_query |= Q(stream__icontains=stream)
        if stream_query:
            students = students.filter(stream_query)

    try:
        if min_tenth:
            students = students.filter(tenth_percent__gte=float(min_tenth))
        if min_twelfth:
            students = students.filter(twelfth_percent__gte=float(min_twelfth))
        if min_degree:
            students = students.filter(degree_percent__gte=float(min_degree))
        if min_yop:
            students = students.filter(yop__gte=int(min_yop))
        if max_yop:
            students = students.filter(yop__lte=int(max_yop))
    except ValueError:
        pass

    if gender_filter:
        students = students.filter(gender__iexact=gender_filter)

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(contact_number__icontains=search_query) |
            Q(degree__icontains=search_query) |
            Q(stream__icontains=search_query)
        )

    ordering_map = {
        'total_requirements': '-total_requirements_count',
        'scheduled_requirements': '-scheduled_requirements_count',
        'yop': '-yop',
        'tenth_percent': '-tenth_percent',
        'twelfth_percent': '-twelfth_percent',
        'degree_percent': '-degree_percent'
    }

    if sort_by in ordering_map:
        students = students.order_by(ordering_map[sort_by], 'name')
    elif sort_by.startswith('-'):
        students = students.order_by(f'{sort_by}', 'name')
    else:
        students = students.order_by(sort_by, 'name')

    unique_degrees = Student.objects.values_list('degree', flat=True).distinct().order_by('degree')
    unique_streams = Student.objects.values_list('stream', flat=True).distinct().order_by('stream')

    paginator = Paginator(students, 50)
    page_obj = paginator.get_page(page_number)

    type_counts = {
        'all': Student.objects.count(),
        'fsdi': Student.objects.filter(type_of_data__iexact='fsdi').count(),
        'super100': Student.objects.filter(type_of_data__iexact='super100').count(),
        'fastrack': Student.objects.filter(type_of_data__iexact='fastrack').count(),
        'legend': Student.objects.filter(type_of_data__iexact='legend').count(),
    }

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
        'type_filter': type_filter,
        'total_count': students.count(),
        'type_counts': type_counts,

        'degree_filter': degree_filter,
        'stream_filters': stream_filters,
        'min_tenth': min_tenth,
        'min_twelfth': min_twelfth,
        'min_degree': min_degree,
        'gender_filter': gender_filter,
        'min_yop': min_yop,
        'max_yop': max_yop,

        'unique_degrees': unique_degrees,
        'unique_streams': unique_streams,

        'sort_options': [
            ('name', 'Name'),
            ('yop', 'Year of Passing'),
            ('tenth_percent', '10th Percentage'),
            ('twelfth_percent', '12th Percentage'),
            ('degree_percent', 'Degree Percentage'),
            ('total_requirements', 'Total Requirements'),
            ('scheduled_requirements', 'Scheduled Requirements'),
            ('gender', 'Gender'),
            ('type_of_data', 'Type of Data'),
            ('created_at', 'Created Date'),
        ]
    }

    return render(request, 'studentlist.html', context)


def student_detail(request, student_id):
    # Annotate the student object with counts
    student = get_object_or_404(
        Student.objects.annotate(
            total_requirements_count=Count('requirementstudent'),
            scheduled_requirements_count=Count(
                'requirementstudent',
                filter=Q(requirementstudent__requirement__is_scheduled=True)
            )
        ),
        pk=student_id
    )

    student_requirements = (
        RequirementStudent.objects
        .filter(student=student)
        .select_related('requirement')
        .order_by('-requirement__created_at')
    )

    context = {
        'student': student,
        'student_requirements': student_requirements,
        'total_requirements': student.total_requirements_count,
        'scheduled_requirements': student.scheduled_requirements_count,
        'js_data': {
            'name': student.name,
            'degree': student.degree,
            'stream': student.stream,
            'degree_percent': float(getattr(student, 'degree_percent', 0.0)),
            'tenth_percent': float(getattr(student, 'tenth_percent', 0.0)),
            'twelfth_percent': float(getattr(student, 'twelfth_percent', 0.0)),
            'total_requirements': student.total_requirements_count,
            'scheduled_requirements': student.scheduled_requirements_count,
        }
    }

    return render(request, 'student_detail.html', context)

import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Requirement, Student, RequirementStudent
from .forms import RequirementForm

import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from .models import Requirement, Student, RequirementStudent
from .forms import RequirementForm, RequirementEditForm

@login_required
def requirement_list(request):
    """View for listing all requirements with filtering and sorting"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-requirement_date')  # Default sort by requirement date (newest first)
    
    # Start with all requirements
    requirements = Requirement.objects.all()
    
    # Apply search filter
    if search_query:
        requirements = requirements.filter(
            Q(company_name__icontains=search_query) | 
            Q(company_code__icontains=search_query)
        )
    
    # Apply status filter
    if status_filter == 'scheduled':
        requirements = requirements.filter(is_scheduled=True)
    elif status_filter == 'pending':
        requirements = requirements.filter(is_scheduled=False)
    
    # Apply sorting
    requirements = requirements.order_by(sort_by)
    
    # Annotate with student count
    requirements = requirements.annotate(student_count=Count('students'))
    
    # Pagination
    paginator = Paginator(requirements, 10)  # Show 10 requirements per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Count by status for statistics
    total_count = Requirement.objects.count()
    scheduled_count = Requirement.objects.filter(is_scheduled=True).count()
    pending_count = Requirement.objects.filter(is_scheduled=False).count()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'total_count': total_count,
        'scheduled_count': scheduled_count,
        'pending_count': pending_count,
    }
    
    return render(request, 'requirement_list.html', context)

@login_required
def add_requirement(request):
    """View for adding a new requirement with student import from Excel"""
    if request.method == 'POST':
        form = RequirementForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the requirement
            requirement = form.save(commit=False)
            requirement.save()
            
            # Process the Excel file if provided
            if 'student_file' in request.FILES:
                try:
                    # Read the Excel file
                    excel_file = request.FILES['student_file']
                    df = pd.read_excel(excel_file)
                    
                    # Get the column containing mobile numbers
                    mobile_column = form.cleaned_data.get('mobile_column', 'mobile')
                    
                    # Track statistics
                    total_students = 0
                    added_students = 0
                    not_found_students = 0
                    
                    # Process each mobile number
                    for index, row in df.iterrows():
                        # Skip if the column doesn't exist
                        if mobile_column not in row:
                            messages.error(request, f"Column '{mobile_column}' not found in the Excel file.")
                            break
                            
                        mobile = str(row[mobile_column]).strip()
                        # Skip empty values
                        if not mobile or mobile == 'nan':
                            continue
                            
                        total_students += 1
                        
                        # Try to find the student by mobile number
                        try:
                            # Normalize the mobile number (remove spaces, etc.)
                            mobile = ''.join(filter(str.isdigit, mobile))
                            
                            # If the mobile number is too short, skip it
                            if len(mobile) < 10:
                                not_found_students += 1
                                continue
                                
                            # Get the last 10 digits if longer
                            if len(mobile) > 10:
                                mobile = mobile[-10:]
                                
                            student = Student.objects.get(contact_number__endswith=mobile)
                            
                            # Add the student to the requirement if not already added
                            if not RequirementStudent.objects.filter(requirement=requirement, student=student).exists():
                                RequirementStudent.objects.create(
                                    requirement=requirement,
                                    student=student
                                )
                                added_students += 1
                                
                        except Student.DoesNotExist:
                            not_found_students += 1
                            continue
                        except Student.MultipleObjectsReturned:
                            # Handle case where multiple students have the same number
                            students = Student.objects.filter(contact_number__endswith=mobile)
                            for student in students:
                                if not RequirementStudent.objects.filter(requirement=requirement, student=student).exists():
                                    RequirementStudent.objects.create(
                                        requirement=requirement,
                                        student=student
                                    )
                                    added_students += 1
                    
                    # Show success message with statistics
                    messages.success(request, 
                        f'Requirement created successfully! '
                        f'Added {added_students} students out of {total_students} from the file. '
                        f'{not_found_students} students were not found in the database.'
                    )
                    
                except Exception as e:
                    messages.error(request, f'Error processing Excel file: {str(e)}')
                    return redirect('requirement_detail', requirement.id)
            else:
                messages.success(request, 'Requirement created successfully! No students were added.')
                
            return redirect('requirement_detail', requirement.id)
    else:
        form = RequirementForm()
    
    return render(request, 'add_requirement.html', {
        'form': form,
        'title': 'Add New Requirement'
    })

@login_required
def requirement_detail(request, pk):
    """View for showing requirement details and assigned students"""
    requirement = get_object_or_404(Requirement, pk=pk)
    
    # Get all students assigned to this requirement with their status
    requirement_students = RequirementStudent.objects.filter(requirement=requirement).select_related('student')
    
    # Get statistics
    total_students = requirement_students.count()
    selected_students = requirement_students.filter(status='selected').count()
    rejected_students = requirement_students.filter(status='rejected').count()
    pending_students = requirement_students.filter(status='pending').count()
    on_hold_students = requirement_students.filter(status='on_hold').count()
    
    context = {
        'requirement': requirement,
        'requirement_students': requirement_students,
        'total_students': total_students,
        'selected_students': selected_students,
        'rejected_students': rejected_students,
        'pending_students': pending_students,
        'on_hold_students': on_hold_students,
    }
    
    return render(request, 'requirement_detail.html', context)
@login_required
def requirement_edit(request, pk):
    """View for editing an existing requirement"""
    requirement = get_object_or_404(Requirement, pk=pk)
    
    if request.method == 'POST':
        form = RequirementEditForm(request.POST, instance=requirement)
        if form.is_valid():
            form.save()
            messages.success(request, 'Requirement updated successfully!')
            return redirect('requirement_detail', pk=requirement.id)
    else:
        form = RequirementEditForm(instance=requirement)
    
    return render(request, 'requirement_edit.html', {
        'form': form,
        'requirement': requirement,
        'title': 'Edit Requirement'
    })


from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from .models import Requirement, Student, RequirementStudent
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Requirement, Student, RequirementStudent
@login_required
def requirement_students(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    
    # Get all assigned students
    assigned_requirement_students = RequirementStudent.objects.filter(requirement=requirement)
    assigned_student_ids = list(assigned_requirement_students.values_list('student_id', flat=True))

    # Initialize available students queryset
    available_students = Student.objects.all()

    # Handle filters
    filters = {
        'search': request.GET.get('search', ''),
        'degrees': request.GET.getlist('degree', []),  # Changed to getlist for multiple selection
        'streams': request.GET.getlist('stream', []),  # Changed to getlist for multiple selection
        'gender': request.GET.get('gender', ''),
        'min_percentage': request.GET.get('min_percentage', ''),
        'min_yop': request.GET.get('min_yop', ''),
        'max_yop': request.GET.get('max_yop', ''),
        'show_assigned': request.GET.get('show_assigned', 'false') == 'true'
    }

    # Build query based on filters
    query = Q()

    # Search filter
    if filters['search']:
        query |= (Q(name__icontains=filters['search']) |
                 Q(contact_number__icontains=filters['search']) |
                 Q(email__icontains=filters['search']))

    # Multiple degree filter
    if filters['degrees']:
        query &= Q(degree__in=filters['degrees'])

    # Multiple stream filter
    if filters['streams']:
        query &= Q(stream__in=filters['streams'])

    # Gender filter
    if filters['gender']:
        query &= Q(gender=filters['gender'])

    # Percentage filter
    if filters['min_percentage']:
        try:
            query &= Q(degree_percent__gte=float(filters['min_percentage']))
        except ValueError:
            pass

    # Year of passing filters
    if filters['min_yop']:
        try:
            query &= Q(yop__gte=int(filters['min_yop']))
        except ValueError:
            pass

    if filters['max_yop']:
        try:
            query &= Q(yop__lte=int(filters['max_yop']))
        except ValueError:
            pass

    # Apply filters to queryset
    available_students = available_students.filter(query)

    # Exclude assigned students if show_assigned is False
    if not filters['show_assigned']:
        available_students = available_students.exclude(id__in=assigned_student_ids)

    # Handle POST requests
    if request.method == 'POST':
        action = request.POST.get('action')
        student_ids = request.POST.getlist('student_ids')

        if action == 'add' and student_ids:
            added_count = 0
            existing_count = 0
            for sid in student_ids:
                try:
                    student = Student.objects.get(pk=sid)
                    _, created = RequirementStudent.objects.get_or_create(
                        requirement=requirement,
                        student=student,
                        defaults={'status': 'pending'}
                    )
                    if created:
                        added_count += 1
                    else:
                        existing_count += 1
                except Student.DoesNotExist:
                    continue

            if added_count > 0:
                messages.success(request, f'{added_count} students successfully added.')
            if existing_count > 0:
                messages.info(request, f'{existing_count} students were already assigned.')
            
            return redirect('requirement_students', pk=requirement.id)

        elif action == 'update_status' and student_ids:
            new_status = request.POST.get('new_status')
            if new_status in ['pending', 'selected', 'rejected', 'on_hold']:
                updated = RequirementStudent.objects.filter(
                    requirement=requirement,
                    student_id__in=student_ids
                ).update(status=new_status)
                messages.success(request, f'Status updated for {updated} students.')
            
            return redirect('requirement_students', pk=requirement.id)

    # Pagination
    page_size = int(request.GET.get('page_size', 12))
    paginator = Paginator(available_students.order_by('-created_at'), page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # Get unique values for filters
    unique_degrees = Student.objects.values_list('degree', flat=True).distinct().order_by('degree')
    unique_streams = Student.objects.values_list('stream', flat=True).distinct().order_by('stream')

    context = {
        'requirement': requirement,
        'page_obj': page_obj,
        'assigned_students': assigned_requirement_students.select_related('student'),
        'filters': filters,
        'unique_degrees': unique_degrees,
        'unique_streams': unique_streams,
        'total_available': available_students.count(),
        'total_assigned': assigned_requirement_students.count(),
        'page_size_options': [12, 24, 48, 96],
        'current_page_size': page_size,
    }

    return render(request, 'requirement_students.html', context)

@login_required
def update_student_status(request, requirement_id, student_id):
    """View for updating a student's status in a requirement"""
    requirement = get_object_or_404(Requirement, pk=requirement_id)
    student = get_object_or_404(Student, pk=student_id)
    
    # Check if the student is assigned to this requirement
    requirement_student = get_object_or_404(RequirementStudent, requirement=requirement, student=student)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'selected', 'rejected', 'on_hold']:
            requirement_student.status = new_status
            requirement_student.save()
            messages.success(request, f'Updated status for {student.name} to {new_status}.')
    
    # Redirect back to the requirement detail page
    return redirect('requirement_detail', pk=requirement_id)
@login_required
def bulk_import_students(request, requirement_id):
    """View for bulk importing students to a requirement from Excel"""
    requirement = get_object_or_404(Requirement, pk=requirement_id)
    
    if request.method == 'POST' and 'student_file' in request.FILES:
        try:
            # Read the Excel file
            excel_file = request.FILES['student_file']
            df = pd.read_excel(excel_file)
            
            # Get the column containing mobile numbers
            mobile_column = request.POST.get('mobile_column', 'mobile')
            
            # Track statistics
            total_students = 0
            added_students = 0
            not_found_students = 0
            already_assigned = 0
            
            # Process each mobile number
            for index, row in df.iterrows():
                # Skip if the column doesn't exist
                if mobile_column not in row:
                    messages.error(request, f"Column '{mobile_column}' not found in the Excel file.")
                    break
                    
                mobile = str(row[mobile_column]).strip()
                # Skip empty values
                if not mobile or mobile == 'nan':
                    continue
                    
                total_students += 1
                
                # Try to find the student by mobile number
                try:
                    # Normalize the mobile number (remove spaces, etc.)
                    mobile = ''.join(filter(str.isdigit, mobile))
                    
                    # If the mobile number is too short, skip it
                    if len(mobile) < 10:
                        not_found_students += 1
                        continue
                        
                    # Get the last 10 digits if longer
                    if len(mobile) > 10:
                        mobile = mobile[-10:]
                        
                    student = Student.objects.get(contact_number__endswith=mobile)
                    
                    # Add the student to the requirement if not already added
                    if not RequirementStudent.objects.filter(requirement=requirement, student=student).exists():
                        RequirementStudent.objects.create(
                            requirement=requirement,
                            student=student
                        )
                        added_students += 1
                    else:
                        already_assigned += 1
                        
                except Student.DoesNotExist:
                    not_found_students += 1
                    continue
                except Student.MultipleObjectsReturned:
                    # Handle case where multiple students have the same number
                    students = Student.objects.filter(contact_number__endswith=mobile)
                    for student in students:
                        if not RequirementStudent.objects.filter(requirement=requirement, student=student).exists():
                            RequirementStudent.objects.create(
                                requirement=requirement,
                                student=student
                            )
                            added_students += 1
                        else:
                            already_assigned += 1
            
            # Show success message with statistics
            messages.success(request, 
                f'Import completed! '
                f'Added {added_students} students out of {total_students} from the file. '
                f'{not_found_students} students were not found in the database. '
                f'{already_assigned} students were already assigned to this requirement.'
            )
            
        except Exception as e:
            messages.error(request, f'Error processing Excel file: {str(e)}')
    
    # Redirect back to the requirement students page
    return redirect('requirement_students', pk=requirement_id)

@login_required
def remove_requirement_student(request, requirement_id, student_id):
    requirement_student = get_object_or_404(
        RequirementStudent, 
        requirement_id=requirement_id,
        student_id=student_id
    )
    
    try:
        requirement_student.delete()
        messages.success(request, "Student successfully removed from requirement.")
    except Exception as e:
        messages.error(request, f"Error removing student: {str(e)}")
    
    return redirect('requirement_students', pk=requirement_id)

@login_required
def bulk_remove_requirement_students(request, requirement_id):
    student_ids = request.POST.getlist('student_ids', [])
    
    if not student_ids:
        messages.warning(request, "No students selected for removal.")
        return redirect('requirement_students', pk=requirement_id)
    
    try:
        deleted_count = RequirementStudent.objects.filter(
            requirement_id=requirement_id,
            student_id__in=student_ids
        ).delete()[0]
        
        messages.success(request, f"{deleted_count} students successfully removed from requirement.")
    except Exception as e:
        messages.error(request, f"Error removing students: {str(e)}")
    
    return redirect('requirement_students', pk=requirement_id)


from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db.models import F

@login_required
def add_students_to_requirement(request, requirement_id):
    requirement = get_object_or_404(Requirement, id=requirement_id)
    student_ids = request.POST.getlist('student_ids')
    
    if student_ids:
        added_count = 0
        
        with transaction.atomic():
            for student_id in student_ids:
                try:
                    student = Student.objects.get(id=student_id)
                    
                    # Try to create the relationship
                    _, created = RequirementStudent.objects.get_or_create(
                        student=student,
                        requirement=requirement,
                        defaults={
                            'status': 'pending',
                            'created_at': timezone.now()
                        }
                    )
                    
                    if created:
                        # Update student counts
                        Student.objects.filter(id=student.id).update(
                            total_requirements=F('total_requirements') + 1
                        )
                        
                        # If requirement is scheduled, update scheduled count
                        if requirement.schedule_status == 'scheduled':
                            Student.objects.filter(id=student.id).update(
                                scheduled_requirements=F('scheduled_requirements') + 1
                            )
                        
                        added_count += 1
                        
                except Student.DoesNotExist:
                    continue
            
            if added_count > 0:
                # Refresh requirement to get updated counts
                requirement.refresh_from_db()
                
                messages.success(
                    request, 
                    f'{added_count} students added to requirement successfully. '
                    f'Total students: {requirement.students.count()}'
                )

    return redirect('requirements:requirement_detail', pk=requirement_id)

@login_required# Add this view for updating student status
def update_student_status(request, requirement_id, student_id):
    with transaction.atomic():
        requirement_student = get_object_or_404(
            RequirementStudent,
            requirement_id=requirement_id,
            student_id=student_id
        )
        
        old_status = requirement_student.status
        new_status = request.POST.get('status')
        
        if new_status in dict(RequirementStudent.STATUS_CHOICES):
            requirement_student.status = new_status
            requirement_student.save()
            
            # Update student's requirement counts
            student = requirement_student.student
            student.update_requirement_counts()
            
            messages.success(
                request, 
                f'Status updated to {dict(RequirementStudent.STATUS_CHOICES)[new_status]}'
            )
        
    return redirect('requirements:requirement_detail', pk=requirement_id)

# Add this view for removing students
@login_required
def remove_student_from_requirement(request, requirement_id, student_id):
    with transaction.atomic():
        requirement_student = get_object_or_404(
            RequirementStudent,
            requirement_id=requirement_id,
            student_id=student_id
        )
        
        student = requirement_student.student
        requirement = requirement_student.requirement
        
        # Delete the relationship
        requirement_student.delete()
        
        # Update student counts
        student.update_requirement_counts()
        
        messages.success(request, f'Student removed from requirement successfully.')
    
    return redirect('requirements:requirement_detail', pk=requirement_id)

# Add this view for bulk removing students
@login_required
def bulk_remove_students(request, requirement_id):
    student_ids = request.POST.getlist('student_ids')
    
    if student_ids:
        with transaction.atomic():
            # Get all affected students first
            students = Student.objects.filter(
                id__in=student_ids,
                requirementstudent__requirement_id=requirement_id
            )
            
            # Delete the relationships
            deleted_count = RequirementStudent.objects.filter(
                requirement_id=requirement_id,
                student_id__in=student_ids
            ).delete()[0]
            
            # Update counts for all affected students
            for student in students:
                student.update_requirement_counts()
            
            messages.success(
                request, 
                f'{deleted_count} students removed from requirement successfully.'
            )
    
    return redirect('requirements:requirement_detail', pk=requirement_id)


from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction
@login_required
def update_requirement_schedule(request, requirement_id):
    if request.method == 'POST':
        requirement = get_object_or_404(Requirement, id=requirement_id)
        new_status = request.POST.get('schedule_status')
        
        if new_status in dict(Requirement.SCHEDULE_STATUS_CHOICES):
            try:
                with transaction.atomic():
                    # Update requirement status
                    requirement.schedule_status = new_status
                    requirement.save()
                    
                    messages.success(
                        request, 
                        f'Requirement schedule status updated to {requirement.get_schedule_status_display()}'
                    )
            except Exception as e:
                messages.error(request, f'Error updating schedule status: {str(e)}')
        else:
            messages.error(request, 'Invalid schedule status')
    
    return redirect('requirement_detail', pk=requirement_id)


# views.py
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Count
from datetime import datetime, time
from .models import Student, Requirement, RequirementStudent
@login_required
def home_dashboard(request):
    today = timezone.now().date()
    
    # Get counts and data for dashboard
    context = {
        'total_students': Student.objects.count(),
        'total_requirements': Requirement.objects.count(),
        'scheduled_today': Requirement.objects.filter(
            schedule_status='scheduled',
            schedule_date=today
        ).count(),
        
        # Get latest requirements
        'latest_requirements': Requirement.objects.all().order_by('-created_at')[:5],
        
        # Get today's scheduled requirements
        'todays_requirements': Requirement.objects.filter(
            schedule_status='scheduled',
            schedule_date=today
        ).order_by('schedule_time'),
        
        # Get recent students
        'recent_students': Student.objects.all().order_by('-created_at')[:5],
        
        # Get requirements by status
        'requirement_stats': Requirement.objects.values('schedule_status').annotate(
            count=Count('id')
        ),
    }
    
    return render(request, 'home_dashboard.html', context)


from django.shortcuts import render
from django.db.models import Count, Avg
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json

from .models import Student, RequirementStudent
@login_required
def student_analytics(request):
    # Convert student data to DataFrame
    students = Student.objects.all().values(
        'name', 'degree', 'stream', 'tenth_percent', 
        'twelfth_percent', 'degree_percent', 'type_of_data'
    )
    df = pd.DataFrame(list(students))

    # 1. Distribution of Students by Type
    type_distribution = df['type_of_data'].value_counts()
    type_chart = px.pie(
        values=type_distribution.values,
        names=type_distribution.index,
        title='Distribution of Students by Type',
        template='plotly_dark'
    )

    # 2. Performance Analysis
    performance_fig = go.Figure()
    performance_fig.add_trace(go.Box(y=df['tenth_percent'], name='10th'))
    performance_fig.add_trace(go.Box(y=df['twelfth_percent'], name='12th'))
    performance_fig.add_trace(go.Box(y=df['degree_percent'], name='Degree'))
    performance_fig.update_layout(
        title='Performance Distribution Across Education Levels',
        yaxis_title='Percentage',
        template='plotly_dark'
    )

    # 3. Stream-wise Analysis
    stream_avg = df.groupby('stream')[['tenth_percent', 'twelfth_percent', 'degree_percent']].mean()
    stream_fig = px.bar(
        stream_avg,
        title='Average Performance by Stream',
        barmode='group',
        template='plotly_dark'
    )

    # 4. Requirements Analysis
    requirements_data = RequirementStudent.objects.values(
        'requirement__company_name'
    ).annotate(
        count=Count('id'),
        scheduled=Count('id', filter=Q(requirement__is_scheduled=True))
    )
    req_df = pd.DataFrame(list(requirements_data))
    
    if not req_df.empty:
        req_fig = px.bar(
            req_df,
            x='requirement__company_name',
            y=['count', 'scheduled'],
            title='Requirements Status by Company',
            template='plotly_dark'
        )
    else:
        req_fig = go.Figure()

    # Convert figures to JSON for template
    charts = {
        'type_distribution': type_chart.to_json(),
        'performance_analysis': performance_fig.to_json(),
        'stream_analysis': stream_fig.to_json(),
        'requirements_analysis': req_fig.to_json(),
    }

    # Calculate summary statistics
    summary_stats = {
        'total_students': len(df),
        'avg_degree_percent': df['degree_percent'].mean(),
        'top_stream': df['stream'].mode().iloc[0],
        'type_counts': df['type_of_data'].value_counts().to_dict()
    }

    context = {
        'charts': charts,
        'summary_stats': summary_stats,
    }

    return render(request, 'analytics/student_analytics.html', context)
@login_required
def performance_trends(request):
    # Get all student data
    students = Student.objects.all().values(
        'name', 'tenth_percent', 'twelfth_percent', 
        'degree_percent', 'type_of_data', 'stream'
    )
    df = pd.DataFrame(list(students))

    # 1. Performance Progression
    fig = make_subplots(rows=2, cols=2)

    # Overall progression
    fig.add_trace(
        go.Scatter(
            x=['10th', '12th', 'Degree'],
            y=[df['tenth_percent'].mean(), 
               df['twelfth_percent'].mean(), 
               df['degree_percent'].mean()],
            name='Average Progression'
        ),
        row=1, col=1
    )

    # Type-wise performance
    for student_type in df['type_of_data'].unique():
        type_df = df[df['type_of_data'] == student_type]
        fig.add_trace(
            go.Box(
                y=type_df['degree_percent'],
                name=student_type,
                showlegend=True
            ),
            row=1, col=2
        )

    # Stream-wise performance
    stream_perf = df.groupby('stream')['degree_percent'].mean().sort_values(ascending=False)
    fig.add_trace(
        go.Bar(
            x=stream_perf.index,
            y=stream_perf.values,
            name='Stream Performance'
        ),
        row=2, col=1
    )

    # Performance correlation
    fig.add_trace(
        go.Scatter(
            x=df['twelfth_percent'],
            y=df['degree_percent'],
            mode='markers',
            name='12th vs Degree'
        ),
        row=2, col=2
    )

    fig.update_layout(height=800, title_text="Performance Analysis Dashboard")
    
    context = {
        'performance_dashboard': fig.to_json(),
    }

    return render(request, 'analytics/performance_trends.html', context)