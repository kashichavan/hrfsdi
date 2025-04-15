from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import Student, Requirement, RequirementStudent
from .forms import RequirementForm, RequirementEditForm
import pandas as pd
import re
import threading
import uuid
import json
import os
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Utility functions
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

        df = df.drop_duplicates(subset=['contact_number'], keep='first')
        
        total_rows = len(df)
        chunk_size = 1000
        processed_rows = 0
        duplicates_count = 0

        with transaction.atomic():
            for start in range(0, total_rows, chunk_size):
                end = min(start + chunk_size, total_rows)
                chunk_df = df.iloc[start:end]
                
                for _, row in chunk_df.iterrows():
                    if pd.isna(row.get('name', '')) or pd.isna(row.get('contact_number', '')):
                        continue
                        
                    contact_number = row.get('contact_number', '')
                    
                    try:
                        existing_student = Student.objects.get(contact_number=contact_number)
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

# Student views
@login_required
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

@login_required
def processing_page(request):
    task_id = request.session.get('excel_task_id')
    if not task_id:
        return redirect('upload_excel')
    return render(request, 'processing.html', {'task_id': task_id})

@login_required
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
    except:
        return JsonResponse({'status': 'error', 'message': 'Invalid task status data'})


from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.shortcuts import render

from .models import Student  # Make sure this import exists and matches your actual model location
@login_required
def student_list(request):
    # Get filter params
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

    # Start with base queryset
    students = Student.objects.all()

    # Apply type_of_data filter
    if type_filter:
        if type_filter.lower() != 'all':
            if type_filter.lower() == 'placement_activity':
                students = students.filter(type_of_data__iexact='placement activity')
            else:
                students = students.filter(type_of_data__iexact=type_filter.lower())

    # Filter by degree
    if degree_filter:
        students = students.filter(degree__icontains=degree_filter)

    # Filter by stream(s)
    if stream_filters:
        stream_query = Q()
        for stream in stream_filters:
            if stream:
                stream_query |= Q(stream__icontains=stream)
        if stream_query:
            students = students.filter(stream_query)

    # Filter by percentages and year
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
        pass  # Ignore bad inputs silently

    # Filter by gender
    if gender_filter:
        students = students.filter(gender__iexact=gender_filter)

    # Search by name or contact number
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    # Sorting
    ordering_map = {
        'total_requirements': '-total_requirements',
        'scheduled_requirements': '-scheduled_requirements',
        'yop': '-yop',
        'tenth_percent': '-tenth_percent',
        'twelfth_percent': '-twelfth_percent',
        'degree_percent': '-degree_percent'
    }

    if sort_by in ordering_map:
        students = students.order_by(ordering_map[sort_by], 'name')
    elif sort_by.startswith('-'):
        students = students.order_by(sort_by, 'name')
    else:
        students = students.order_by(sort_by, 'name')

    # For dropdowns
    unique_degrees = Student.objects.values_list('degree', flat=True).distinct().order_by('degree')
    unique_streams = Student.objects.values_list('stream', flat=True).distinct().order_by('stream')

    # Pagination
    paginator = Paginator(students, 50)
    page_obj = paginator.get_page(page_number)

    # Counts for each type_of_data category
    type_counts = {
        'all': Student.objects.count(),
        'fsdi': Student.objects.filter(type_of_data__iexact='fsdi').count(),
        'super100': Student.objects.filter(type_of_data__iexact='super100').count(),
        'fastrack': Student.objects.filter(type_of_data__iexact='fastrack').count(),
        'legend': Student.objects.filter(type_of_data__iexact='legend').count(),
        'placement_activity': Student.objects.filter(type_of_data__iexact='placement activity').count(),
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

    return render(request, 'student_list.html', context)


@login_required
def student_detail(request, student_id):
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

# Requirement views
@login_required
def requirement_list(request):
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    sort_by = request.GET.get('sort', '-requirement_date')
    
    requirements = Requirement.objects.all()
    
    if search_query:
        requirements = requirements.filter(
            Q(company_name__icontains=search_query) | 
            Q(company_code__icontains=search_query)
        )
    
    if status_filter == 'scheduled':
        requirements = requirements.filter(is_scheduled=True)
    elif status_filter == 'pending':
        requirements = requirements.filter(is_scheduled=False)
    
    requirements = requirements.order_by(sort_by).annotate(student_count=Count('students'))
    
    paginator = Paginator(requirements, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
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

from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import RequirementForm
from .models import Student, RequirementStudent
import pandas as pd

@login_required
def add_requirement(request):
    if request.method == 'POST':
        form = RequirementForm(request.POST, request.FILES)
        if form.is_valid():
            requirement = form.save(commit=False)

            # ✅ Automatically update schedule_status based on is_scheduled
            if requirement.is_scheduled:
                requirement.schedule_status = 'scheduled'
            else:
                requirement.schedule_status = 'not_scheduled'

            requirement.save()

            if 'student_file' in request.FILES:
                try:
                    excel_file = request.FILES['student_file']
                    df = pd.read_excel(excel_file)
                    
                    mobile_column = form.cleaned_data.get('mobile_column', 'mobile')
                    total_students = 0
                    added_students = 0
                    not_found_students = 0
                    
                    for index, row in df.iterrows():
                        if mobile_column not in row:
                            messages.error(request, f"Column '{mobile_column}' not found in the Excel file.")
                            break
                            
                        mobile = str(row[mobile_column]).strip()
                        if not mobile or mobile == 'nan':
                            continue
                            
                        total_students += 1
                        
                        try:
                            mobile = ''.join(filter(str.isdigit, mobile))
                            
                            if len(mobile) < 10:
                                not_found_students += 1
                                continue
                                
                            if len(mobile) > 10:
                                mobile = mobile[-10:]
                                
                            student = Student.objects.get(contact_number__endswith=mobile)
                            
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
                            students = Student.objects.filter(contact_number__endswith=mobile)
                            for student in students:
                                if not RequirementStudent.objects.filter(requirement=requirement, student=student).exists():
                                    RequirementStudent.objects.create(
                                        requirement=requirement,
                                        student=student
                                    )
                                    added_students += 1
                    
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
                
            return redirect('student_data:requirement_detail', requirement.id)
    else:
        form = RequirementForm()
    
    return render(request, 'add_requirement.html', {
        'form': form,
        'title': 'Add New Requirement'
    })

@login_required
def requirement_detail(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    requirement_students = RequirementStudent.objects.filter(requirement=requirement).select_related('student')
    
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
    requirement = get_object_or_404(Requirement, pk=pk)
    
    if request.method == 'POST':
        form = RequirementEditForm(request.POST, instance=requirement)
        if form.is_valid():
            requirement = form.save(commit=False)

            # ✅ Update schedule_status if scheduled
            if requirement.is_scheduled:
                requirement.schedule_status = 'scheduled'
            else:
                requirement.schedule_status = 'not_scheduled'

            requirement.save()

            # ✅ Update scheduled counts for each student
            for student in requirement.students.all():
                student.update_requirement_counts()

            messages.success(request, 'Requirement updated successfully!')
            return redirect('student_data:requirement_detail', pk=requirement.id)
    else:
        form = RequirementEditForm(instance=requirement)
    
    return render(request, 'requirement_edit.html', {
        'form': form,
        'requirement': requirement,
        'title': 'Edit Requirement'
    })

@login_required
def requirement_students(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    assigned_requirement_students = RequirementStudent.objects.filter(requirement=requirement)
    assigned_student_ids = list(assigned_requirement_students.values_list('student_id', flat=True))

    available_students = Student.objects.all()

    filters = {
        'search': request.GET.get('search', ''),
        'degrees': request.GET.getlist('degree', []),
        'streams': request.GET.getlist('stream', []),
        'gender': request.GET.get('gender', ''),
        'min_percentage': request.GET.get('min_percentage', ''),
        'min_yop': request.GET.get('min_yop', ''),
        'max_yop': request.GET.get('max_yop', ''),
        'show_assigned': request.GET.get('show_assigned', 'false') == 'true'
    }

    query = Q()

    if filters['search']:
        query |= (Q(name__icontains=filters['search']) |
                 Q(contact_number__icontains=filters['search']) |
                 Q(email__icontains=filters['search']))

    if filters['degrees']:
        query &= Q(degree__in=filters['degrees'])

    if filters['streams']:
        query &= Q(stream__in=filters['streams'])

    if filters['gender']:
        query &= Q(gender=filters['gender'])

    if filters['min_percentage']:
        try:
            query &= Q(degree_percent__gte=float(filters['min_percentage']))
        except ValueError:
            pass

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

    available_students = available_students.filter(query)

    if not filters['show_assigned']:
        available_students = available_students.exclude(id__in=assigned_student_ids)

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
            
            return redirect('student_data:requirement_students', pk=requirement.id)

        elif action == 'update_status' and student_ids:
            new_status = request.POST.get('new_status')
            if new_status in ['pending', 'selected', 'rejected', 'on_hold']:
                updated = RequirementStudent.objects.filter(
                    requirement=requirement,
                    student_id__in=student_ids
                ).update(status=new_status)
                messages.success(request, f'Status updated for {updated} students.')
            
            return redirect('requirement_students', pk=requirement.id)

    page_size = int(request.GET.get('page_size', 12))
    paginator = Paginator(available_students.order_by('-created_at'), page_size)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

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
    requirement = get_object_or_404(Requirement, pk=requirement_id)
    student = get_object_or_404(Student, pk=student_id)
    requirement_student = get_object_or_404(RequirementStudent, requirement=requirement, student=student)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['pending', 'selected', 'rejected', 'on_hold']:
            requirement_student.status = new_status
            requirement_student.save()
            messages.success(request, f'Updated status for {student.name} to {new_status}.')
    
    return redirect('requirement_detail', pk=requirement_id)

@login_required
def bulk_import_students(request, requirement_id):
    requirement = get_object_or_404(Requirement, pk=requirement_id)
    
    if request.method == 'POST' and 'student_file' in request.FILES:
        try:
            excel_file = request.FILES['student_file']
            df = pd.read_excel(excel_file)
            
            mobile_column = request.POST.get('mobile_column', 'mobile')
            total_students = 0
            added_students = 0
            not_found_students = 0
            already_assigned = 0
            
            for index, row in df.iterrows():
                if mobile_column not in row:
                    messages.error(request, f"Column '{mobile_column}' not found in the Excel file.")
                    break
                    
                mobile = str(row[mobile_column]).strip()
                if not mobile or mobile == 'nan':
                    continue
                    
                total_students += 1
                
                try:
                    mobile = ''.join(filter(str.isdigit, mobile))
                    
                    if len(mobile) < 10:
                        not_found_students += 1
                        continue
                        
                    if len(mobile) > 10:
                        mobile = mobile[-10:]
                        
                    student = Student.objects.get(contact_number__endswith=mobile)
                    
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
            
            messages.success(request, 
                f'Import completed! '
                f'Added {added_students} students out of {total_students} from the file. '
                f'{not_found_students} students were not found in the database. '
                f'{already_assigned} students were already assigned to this requirement.'
            )
            
        except Exception as e:
            messages.error(request, f'Error processing Excel file: {str(e)}')
    
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


from django.shortcuts import render, get_object_or_404, redirect
from .models import Student, Requirement, RequirementStudent
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Student, Requirement, RequirementStudent

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Student, Requirement, RequirementStudent
from django.core.paginator import Paginator

def add_students_to_requirement(request, requirement_id):
    requirement = get_object_or_404(Requirement, id=requirement_id)
    
    # Get IDs of students already assigned to this requirement
    already_assigned_student_ids = RequirementStudent.objects.filter(
        requirement=requirement
    ).values_list('student_id', flat=True)
    
    # Get all students not already assigned to this requirement
    students = Student.objects.exclude(id__in=already_assigned_student_ids)
    
    # Initialize filter variables
    search_query = request.GET.get('search', '')
    selected_streams = request.GET.getlist('streams', [])
    year_from = request.GET.get('year_from', '')
    year_to = request.GET.get('year_to', '')
    tenth_percentage = request.GET.get('tenth_percentage', '')
    twelfth_percentage = request.GET.get('twelfth_percentage', '')
    degree_percentage = request.GET.get('degree_percentage', '')
    
    # Apply filters
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) | 
            Q(contact_number__icontains=search_query)
        )
    
    if selected_streams:
        students = students.filter(stream__in=selected_streams)
    
    if year_from:
        students = students.filter(yop__gte=year_from)
    
    if year_to:
        students = students.filter(yop__lte=year_to)
    
    if tenth_percentage:
        students = students.filter(tenth_percent__gte=float(tenth_percentage))
    
    if twelfth_percentage:
        students = students.filter(twelfth_percent__gte=float(twelfth_percentage))
    
    if degree_percentage:
        students = students.filter(degree_percent__gte=float(degree_percentage))
    
    # Get all unique streams for dropdown
    all_streams = Student.objects.values_list('stream', flat=True).distinct()
    
    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids')
        
        # Create StudentRequirement records for selected students
        for student_id in student_ids:
            RequirementStudent.objects.create(
                student_id=student_id,
                requirement=requirement,
            )
        
        return redirect('student_data:requirement_detail', pk=requirement_id)
    
    context = {
        'requirement': requirement,
        'students': students,
        'all_streams': all_streams,
        'selected_streams': selected_streams,
        'search_query': search_query,
        'year_from': year_from,
        'year_to': year_to,
        'tenth_percentage': tenth_percentage,
        'twelfth_percentage': twelfth_percentage,
        'degree_percentage': degree_percentage,
        'already_assigned_student_ids': already_assigned_student_ids,
    }
    
    return render(request, 'add_student_to_requirement.html', context)
# Dashboard views
@login_required
def home_dashboard(request):
    today = timezone.now().date()
    
    context = {
        'total_students': Student.objects.count(),
        'total_requirements': Requirement.objects.count(),
        'scheduled_today': Requirement.objects.filter(
            schedule_status='scheduled',
            schedule_date=today
        ).count(),
        'latest_requirements': Requirement.objects.all().order_by('-created_at')[:5],
        'todays_requirements': Requirement.objects.filter(
            schedule_status='scheduled',
            schedule_date=today
        ).order_by('schedule_time'),
        'recent_students': Student.objects.all().order_by('-created_at')[:5],
        'requirement_stats': Requirement.objects.values('schedule_status').annotate(
            count=Count('id')
        ),
    }
    
    return render(request, 'home_dashboard.html', context)

# Analytics views
@login_required
def student_analytics(request):
    students = Student.objects.all().values(
        'name', 'degree', 'stream', 'tenth_percent', 
        'twelfth_percent', 'degree_percent', 'type_of_data'
    )
    df = pd.DataFrame(list(students))

    type_distribution = df['type_of_data'].value_counts()
    type_chart = px.pie(
        values=type_distribution.values,
        names=type_distribution.index,
        title='Distribution of Students by Type',
        template='plotly_dark'
    )

    performance_fig = go.Figure()
    performance_fig.add_trace(go.Box(y=df['tenth_percent'], name='10th'))
    performance_fig.add_trace(go.Box(y=df['twelfth_percent'], name='12th'))
    performance_fig.add_trace(go.Box(y=df['degree_percent'], name='Degree'))
    performance_fig.update_layout(
        title='Performance Distribution Across Education Levels',
        yaxis_title='Percentage',
        template='plotly_dark'
    )

    stream_avg = df.groupby('stream')[['tenth_percent', 'twelfth_percent', 'degree_percent']].mean()
    stream_fig = px.bar(
        stream_avg,
        title='Average Performance by Stream',
        barmode='group',
        template='plotly_dark'
    )

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

    charts = {
        'type_distribution': type_chart.to_json(),
        'performance_analysis': performance_fig.to_json(),
        'stream_analysis': stream_fig.to_json(),
        'requirements_analysis': req_fig.to_json(),
    }

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
    students = Student.objects.all().values(
        'name', 'tenth_percent', 'twelfth_percent', 
        'degree_percent', 'type_of_data', 'stream'
    )
    df = pd.DataFrame(list(students))

    fig = make_subplots(rows=2, cols=2)

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

    stream_perf = df.groupby('stream')['degree_percent'].mean().sort_values(ascending=False)
    fig.add_trace(
        go.Bar(
            x=stream_perf.index,
            y=stream_perf.values,
            name='Stream Performance'
        ),
        row=2, col=1
    )

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


from django.shortcuts import render
from django.utils import timezone
from .models import Requirement

def todays_requirements_view(request):
    today = timezone.now().date()
    requirements = Requirement.objects.filter(created_at__date=today).order_by('-created_at')
    
    context = {
        'requirements': requirements
    }
    return render(request, 'todays_requirements.html', context)
# views.py
from django.utils import timezone
from django.shortcuts import render
from .models import RequirementStudent

def students_attending_today(request):
    today = timezone.now().date()
    
    students_today = RequirementStudent.objects.filter(
        requirement__schedule_date=today,
        requirement__schedule_status='scheduled'
    ).select_related('student', 'requirement')

    context = {
        'students_today': students_today,
        'today': today
    }
    return render(request, 'students_attending_today.html', context)

import io
import zipfile
import pandas as pd
from django.http import HttpResponse
from django.utils import timezone
from .models import RequirementStudent, Requirement


def export_today_scheduled_requirements(request):
    today = timezone.now().date()
    requirements = Requirement.objects.filter(schedule_date=today, schedule_status='scheduled')
    
    if not requirements.exists():
        return HttpResponse("No scheduled requirements for today.", status=404)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for req in requirements:
            students = req.students.all().values('name', 'contact_number')
            if students:
                df = pd.DataFrame(students)
            else:
                df = pd.DataFrame(columns=['name', 'contact_number'])

            excel_buffer = io.BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)

            filename = f"{req.company_name}_{req.id}_{today}.xlsx".replace(" ", "_")
            zip_file.writestr(filename, excel_buffer.read())

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="scheduled_requirements_{today}.zip"'
    return response
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import Requirement, Student, RequirementStudent

def remove_student_from_requirement(request, requirement_id, student_id):
    if request.method == 'POST':
        requirement = get_object_or_404(Requirement, id=requirement_id)
        student = get_object_or_404(Student, id=student_id)

        try:
            link = RequirementStudent.objects.get(requirement=requirement, student=student)
            link.delete()
            student.update_requirement_counts()

            return JsonResponse({
                'success': True,
                'student_id': student_id,
                'message': f'{student.name} removed successfully'
            })

        except RequirementStudent.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Student is not part of this requirement'
            }, status=400)

    return JsonResponse({'success': False, 'message': 'Invalid request'}, status=405)




from django.shortcuts import render
from django.views.decorators.csrf import requires_csrf_token
from django.template import RequestContext

@requires_csrf_token
def custom_page_not_found_view(request, exception):
    return render(request, "404.html", status=404)

# Temporary view in views.py
def test_404_template(request):
    return render(request, "404.html")


# views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import DeleteView
from .models import Student

class StudentDeleteView(LoginRequiredMixin, DeleteView):
    model = Student
    success_url = reverse_lazy('student_data:student_list')  # Update with your actual URL name
    template_name = 'student_confirm_delete.html'
    context_object_name = 'student'

    def get_queryset(self):
        """Ensure users can only delete their own students if needed"""
        qs = super().get_queryset()
        # Add any additional filtering logic here if needed
        return qs