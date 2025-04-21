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
            return redirect('student_data:processing_page')

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
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404
from .models import Student, RequirementStudent

from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Q
import json

@login_required
def student_list(request):
    # Get filter parameters from request
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-scheduled_requirements')  # Default sort
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
    students = students.exclude(requirementstudent__status='selected')

    # Apply type_of_data filter
    if type_filter:
        type_filter_lower = type_filter.lower()
        if type_filter_lower != 'all':
            # Handle special case for placement activity
            if type_filter_lower == 'placement_activity':
                students = students.filter(
                    Q(type_of_data__iexact='placement_activity') | 
                    Q(type_of_data__iexact='placement activity')
                )
            else:
                students = students.filter(type_of_data__iexact=type_filter_lower)

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
        pass  # Ignore bad inputs

    # Filter by gender
    if gender_filter:
        students = students.filter(gender__iexact=gender_filter)

    # Search filter
    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    # Sorting configuration
    valid_sorts = {
        'name', '-name',
        'yop', '-yop',
        'tenth_percent', '-tenth_percent',
        'twelfth_percent', '-twelfth_percent',
        'degree_percent', '-degree_percent',
        'total_requirements', '-total_requirements',
        'scheduled_requirements', '-scheduled_requirements',
        'gender', '-gender',
        'type_of_data', '-type_of_data',
        'created_at', '-created_at'
    }

    # Validate and apply sorting
    sort_by = sort_by if sort_by in valid_sorts else '-scheduled_requirements'
    students = students.order_by(sort_by, 'name')  # Secondary sort by name

    # Get unique values for filters
    unique_degrees = Student.objects.values_list('degree', flat=True).distinct().order_by('degree')
    unique_streams = Student.objects.values_list('stream', flat=True).distinct().order_by('stream')

    # Pagination
    paginator = Paginator(students, 50)
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.get_page(1)
    except EmptyPage:
        page_obj = paginator.get_page(paginator.num_pages)

    # Type counts for quick filters
    type_counts = {
    'all': Student.objects.exclude(requirementstudent__status='selected').count(),
    'fsdi': Student.objects.filter(type_of_data__iexact='fsdi')
                          .exclude(requirementstudent__status='selected').count(),
    'super100': Student.objects.filter(type_of_data__iexact='super100')
                             .exclude(requirementstudent__status='selected').count(),
    'tuition': Student.objects.filter(type_of_data__iexact='tuition')
                            .exclude(requirementstudent__status='selected').count(),
    'legend': Student.objects.filter(type_of_data__iexact='legend')
                           .exclude(requirementstudent__status='selected').count(),
    'placement_activity': Student.objects.filter(
        Q(type_of_data__iexact='placement_activity') | 
        Q(type_of_data__iexact='placement activity')
    ).exclude(requirementstudent__status='selected').count(),
}

    # Context data
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
        'current_sort': sort_by,
        'sort_options': [
            ('-scheduled_requirements', 'Scheduled (High to Low)'),
            ('scheduled_requirements', 'Scheduled (Low to High)'),
            ('-total_requirements', 'Total (High to Low)'),
            ('total_requirements', 'Total (Low to High)'),
            ('name', 'Name (A-Z)'),
            ('-name', 'Name (Z-A)'),
            ('yop', 'YOP (Oldest)'),
            ('-yop', 'YOP (Newest)'),
            ('tenth_percent', '10th % (Low)'),
            ('-tenth_percent', '10th % (High)'),
            ('twelfth_percent', '12th % (Low)'),
            ('-twelfth_percent', '12th % (High)'),
            ('degree_percent', 'Degree % (Low)'),
            ('-degree_percent', 'Degree % (High)'),
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
from django.core.paginator import Paginator

from django.shortcuts import get_object_or_404

def add_students_to_requirement(request, requirement_id):
    requirement = get_object_or_404(Requirement, id=requirement_id)
    
    # 1. Get students who are SELECTED (placed) for this requirement to exclude
    selected_student_ids = RequirementStudent.objects.filter(
        status='selected'
    ).values_list('student_id', flat=True)
    
    # 2. Maintain existing functionality of already assigned students
    already_assigned_students = requirement.students.all()
    already_assigned_student_ids = already_assigned_students.values_list('id', flat=True)
    
    # 3. Get all requirement students for status display
    requirement_students = RequirementStudent.objects.filter(
        requirement=requirement
    ).select_related('student')
    
    # Create a dictionary of student_id: status for template
    student_status_map = {
        rs.student_id: rs.status 
        for rs in requirement_students
    }

    # Base queryset - exclude only SELECTED students
    students = Student.objects.exclude(
        id__in=selected_student_ids
    ).order_by('scheduled_requirements')

    # Get unique sorted streams from available students
    unique_streams = students.values_list('stream', flat=True).distinct().order_by('stream')

    # Filter handling (same as before)
    search_query = request.GET.get('search', '')
    selected_streams = request.GET.getlist('streams', [])
    year_from = request.GET.get('year_from')
    year_to = request.GET.get('year_to')
    tenth_percentage = request.GET.get('tenth_percentage')
    twelfth_percentage = request.GET.get('twelfth_percentage')
    degree_percentage = request.GET.get('degree_percentage')

    if search_query:
        students = students.filter(
            Q(name__icontains=search_query) |
            Q(contact_number__icontains=search_query)
        )

    if selected_streams:
        students = students.filter(stream__in=selected_streams)

    if year_from and year_to:
        students = students.filter(yop__gte=year_from, yop__lte=year_to)

    if tenth_percentage:
        students = students.filter(tenth_percent__gte=float(tenth_percentage))

    if twelfth_percentage:
        students = students.filter(twelfth_percent__gte=float(twelfth_percentage))

    if degree_percentage:
        students = students.filter(degree_percent__gte=float(degree_percentage))

    # Pagination
    paginator = Paginator(students, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    if request.method == 'POST':
        student_ids = request.POST.getlist('student_ids[]')
        students_to_add = Student.objects.filter(id__in=student_ids)
        
        # Create or update RequirementStudent records
        for student in students_to_add:
            RequirementStudent.objects.update_or_create(
                requirement=requirement,
                student=student,
                defaults={'status': 'pending'}  # Default status
            )
        
        return redirect('student_data:requirement_detail', pk=requirement.id)

    # Enhance students with all needed information for template
    enhanced_students = []
    for student in page_obj.object_list:
        enhanced_students.append({
            'student': student,
            'status': student_status_map.get(student.id),
            'is_assigned': student.id in already_assigned_student_ids
        })

    context = {
        'requirement': requirement,
        'page_obj': page_obj,
        'enhanced_students': enhanced_students,
        'already_assigned_student_ids': already_assigned_student_ids,  # For legacy template support
        'unique_streams': unique_streams,
        'search_query': search_query,
        'selected_streams': selected_streams,
        'year_from': year_from,
        'year_to': year_to,
        'tenth_percentage': tenth_percentage,
        'twelfth_percentage': twelfth_percentage,
        'degree_percentage': degree_percentage,
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
            messages.success(request, f'{student.name} removed successfully from the requirement.')
        except RequirementStudent.DoesNotExist:
            messages.error(request, 'Student is not part of this requirement.')

        return redirect('student_data:requirement_detail', pk=requirement.id)

    messages.error(request, 'Invalid request method.')
    return redirect('student_data:requirement_detail', requirement_id=requirement.id)




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
    
# views.py
from django.shortcuts import redirect
from django.contrib import messages
from .models import Requirement

def delete_all_requirements(request):
    if request.method == 'POST':
        # Delete all requirements (this will also delete entries in RequirementStudent due to FK CASCADE)
        Requirement.objects.all().delete()
        
        messages.success(request, "✅ All requirements deleted and students updated.")
    else:
        messages.error(request, "❌ Invalid request method.")

    return redirect('student_data:requirement_list')  # Replace with your actual list view name

from datetime import datetime
import openpyxl
from django.shortcuts import render
from student_data.models import Requirement

def parse_excel_date(cell_value, row_index, field_name, failed_rows):
    """
    Parse dates from Excel, handling multiple formats with priority to DD-MM-YYYY
    """
    # Handle empty values
    if cell_value is None or (isinstance(cell_value, str) and not cell_value.strip()):
        return None

    # If Excel gave us a datetime object (it auto-parsed as MM/DD)
    if isinstance(cell_value, datetime):
        # Check if the date could be ambiguous (month and day both <= 12)
        if cell_value.month <= 12 and cell_value.day <= 12:
            # Ambiguous date - we'll treat it as DD-MM-YYYY as per user preference
            day = cell_value.month
            month = cell_value.day
            year = cell_value.year
            try:
                return datetime(year, month, day).date()
            except ValueError:
                failed_rows.append(f"Row {row_index}: Invalid date after conversion - {day}-{month}-{year}")
                return None
        else:
            # Not ambiguous - Excel likely parsed it correctly
            return cell_value.date()

    # Handle string dates
    if isinstance(cell_value, str):
        cell_value = cell_value.strip()
        
        # Try DD-MM-YYYY format first (user's preferred format)
        try:
            day, month, year = map(int, cell_value.split('-'))
            return datetime(year, month, day).date()
        except ValueError:
            pass
            
        # Try MM-DD-YYYY format (Excel's preferred format)
        try:
            month, day, year = map(int, cell_value.split('-'))
            return datetime(year, month, day).date()
        except ValueError:
            pass
            
        # Try DD/MM/YYYY format
        try:
            day, month, year = map(int, cell_value.split('/'))
            return datetime(year, month, day).date()
        except ValueError:
            pass
            
        # Try MM/DD/YYYY format
        try:
            month, day, year = map(int, cell_value.split('/'))
            return datetime(year, month, day).date()
        except ValueError:
            pass
            
        # If all parsing attempts fail
        failed_rows.append(
            f"Row {row_index}: Invalid {field_name} format ('{cell_value}') - "
            "must be DD-MM-YYYY, MM-DD-YYYY, DD/MM/YYYY or MM/DD/YYYY"
        )
        return None

    # Handle any other type
    failed_rows.append(f"Row {row_index}: Invalid {field_name} type")
    return None

def upload_requirements_view(request):
    message = None
    success_count = 0
    failed_rows = []

    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        try:
            # Read Excel file
            wb = openpyxl.load_workbook(excel_file, data_only=True)
            sheet = wb.active

            for i, row in enumerate(sheet.iter_rows(min_row=3), start=3):  # Skip header
                try:
                    company_name = row[1].value
                    company_code = row[2].value
                    requirement_date_raw = row[3].value
                    schedule_date_raw = row[4].value

                    # Validate required fields
                    if not company_code or not company_name:
                        failed_rows.append(f"Row {i}: Missing company name/code")
                        continue

                    # Parse dates with strict DD-MM-YYYY handling
                    requirement_date = parse_excel_date(
                        requirement_date_raw, i, "requirement date", failed_rows
                    )
                    if requirement_date is None:
                        continue

                    # Handle optional schedule date
                    schedule_date = None
                    if schedule_date_raw is not None and str(schedule_date_raw).strip():
                        schedule_date = parse_excel_date(
                            schedule_date_raw, i, "schedule date", failed_rows
                        )
                        if schedule_date is None:
                            continue

                    # Save to database
                    Requirement.objects.update_or_create(
                        company_code=company_code,
                        defaults={
                            'company_name': company_name,
                            'requirement_date': requirement_date,
                            'schedule_date': schedule_date,
                            'is_scheduled': schedule_date is not None,
                            'schedule_status': 'scheduled' if schedule_date else 'not_scheduled'
                        }
                    )
                    success_count += 1

                except Exception as e:
                    failed_rows.append(f"Row {i}: Error processing row - {str(e)}")

            message = f"Successfully uploaded {success_count} requirement(s)."
            if failed_rows:
                message += f" Failed to process {len(failed_rows)} row(s)."

        except Exception as e:
            failed_rows.append(f"Error processing file: {str(e)}")
            message = "Failed to process the uploaded file."

    return render(request, 'upload_requirements.html', {
        'message': message,
        'errors': failed_rows
    })

# views.py (add this new view)
import openpyxl
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Requirement, Student, RequirementStudent

# views.py
def map_students_to_requirement_view(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        wb = openpyxl.load_workbook(excel_file, data_only=True)
        sheet = wb.active
        success_count = 0
        errors = []

        # Find column indices by header names
        header_row = next(sheet.iter_rows(min_row=1, max_row=1))
        column_indices = {
            'mobile_number': None,
            'company_code': None
        }

        for idx, cell in enumerate(header_row):
            header_name = str(cell.value).strip().lower()
            if 'mobile' in header_name:
                column_indices['mobile_number'] = idx
            elif 'company' in header_name and 'code' in header_name:
                column_indices['company_code'] = idx

        # Validate headers
        if None in column_indices.values():
            errors.append("Missing required columns: Mobile number and/or Company code")
            messages.error(request, "Invalid file format")
            return render(request, 'map_students.html', {'errors': errors})

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
            try:
                # Get values from correct columns
                mobile = str(row[column_indices['mobile_number']].value).strip()
                company_code = str(row[column_indices['company_code']].value).strip()

                if not mobile or not company_code:
                    errors.append(f"Row {row_idx}: Missing required data")
                    continue

                # Case-sensitive company code lookup
                requirement = Requirement.objects.get(company_code__exact=company_code)
                student = Student.objects.get(contact_number=mobile)

                # Create mapping if not exists
                _, created = RequirementStudent.objects.get_or_create(
                    requirement=requirement,
                    student=student,
                    defaults={'status': 'pending'}
                )

                if created:
                    success_count += 1
                else:
                    errors.append(f"Row {row_idx}: Mapping already exists for {mobile} - {company_code}")

            except Requirement.DoesNotExist:
                errors.append(f"Row {row_idx}: Requirement with code '{company_code}' not found")
            except Student.DoesNotExist:
                errors.append(f"Row {row_idx}: Student with mobile '{mobile}' not found")
            except Exception as e:
                errors.append(f"Row {row_idx}: Error - {str(e)}")

        if success_count > 0:
            messages.success(request, f"Successfully mapped {success_count} students!")
        if errors:
            messages.error(request, f"Completed with {len(errors)} errors")

        return render(request, 'map_students.html', {'errors': errors})

    return render(request, 'map_students.html')


from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.http import urlencode
from .models import Student, Requirement, RequirementStudent


def combined_view(request):
    student = None
    requirement = None
    req_students = None
    mobile_number = request.GET.get("mobile_number")
    company_code = request.GET.get("company_code")

    # Handle POST request for status update
    if request.method == "POST" and 'req_student_id' in request.POST:
        req_student_id = request.POST.get("req_student_id")
        new_status = request.POST.get("status")
        mobile_number = request.POST.get("mobile_number")
        company_code = request.POST.get("company_code")

        try:
            req_student = RequirementStudent.objects.get(id=req_student_id)
            if new_status in dict(RequirementStudent.STATUS_CHOICES):
                req_student.status = new_status
                req_student.save()
                messages.success(request, "Status updated successfully.")
            else:
                messages.error(request, "Invalid status.")
        except RequirementStudent.DoesNotExist:
            messages.error(request, "Mapping not found.")

        redirect_url = reverse('student_data:update_status')
        params = {}
        if mobile_number:
            params['mobile_number'] = mobile_number
        elif company_code:
            params['company_code'] = company_code
        if params:
            redirect_url += '?' + urlencode(params)
        return redirect(redirect_url)

    # Handle GET requests
    if mobile_number:
        try:
            student = Student.objects.get(contact_number=mobile_number)
            req_students = RequirementStudent.objects.filter(student=student).select_related('requirement')
        except Student.DoesNotExist:
            messages.error(request, "Student not found.")

    elif company_code:
        try:
            requirement = Requirement.objects.get(company_code=company_code)
            req_students = RequirementStudent.objects.filter(requirement=requirement).select_related('student')
        except Requirement.DoesNotExist:
            messages.error(request, "Company code not found.")

    context = {
        "student": student,
        "requirement": requirement,
        "req_students": req_students,
        "STATUS_CHOICES": RequirementStudent.STATUS_CHOICES,
        "mobile_number": mobile_number,
        "company_code": company_code,
    }
    return render(request, "combined_template.html", context)


from django.core.paginator import Paginator

def placed_students_view(request):
    placed_students_list = RequirementStudent.objects.filter(
        status='selected'
    ).select_related('student', 'requirement')
    
    # Set how many records per page
    paginator = Paginator(placed_students_list, 10)  # Show 10 students per page
    
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'placed_students.html', {
        'page_obj': page_obj,
        'placed_students': placed_students_list
    })

def delete_requirement(request, pk):
    requirement = get_object_or_404(Requirement, pk=pk)
    
    if request.method == 'POST':
        requirement.delete()
        messages.success(request, f'Requirement "{requirement.company_name}" deleted successfully.')
        return redirect('student_data:requirement_list')
    
    context = {
        'requirement': requirement,
    }
    return render(request, 'delete_requirement.html', context)

import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import Student, RequirementStudent
from io import BytesIO

import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import Student, Requirement, RequirementStudent
from io import BytesIO
from django.core.exceptions import ObjectDoesNotExist

import pandas as pd
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from .models import Student, Requirement, RequirementStudent
from io import BytesIO
from django.core.exceptions import ObjectDoesNotExist

def update_selected_students(request):
    context = {
        'existing_companies': Requirement.objects.exclude(
            company_code__isnull=True
        ).exclude(
            company_code__exact=''
        ).order_by('company_code').values_list('company_code', flat=True).distinct()
    }
    
    if request.method == 'POST':
        try:
            excel_file = request.FILES.get('excel_file')
            mobile_column = request.POST.get('mobile_column', 'mobile_number').strip()
            company_column = request.POST.get('company_column', 'company_code').strip()
            
            if not excel_file:
                raise ValueError("Please upload an Excel file")
            
            # Read Excel file
            try:
                if excel_file.name.endswith('.xlsx'):
                    df = pd.read_excel(excel_file)
                elif excel_file.name.endswith('.csv'):
                    df = pd.read_csv(excel_file)
                else:
                    raise ValueError("Unsupported file format. Please upload .xlsx or .csv")
            except Exception as e:
                raise ValueError(f"Error reading file: {str(e)}")
            
            # Validate columns exist
            for col in [mobile_column, company_column]:
                if col not in df.columns:
                    available_columns = ", ".join(df.columns)
                    raise ValueError(
                        f"Column '{col}' not found in Excel. Available columns: {available_columns}"
                    )
            
            # Clean data
            df = df.dropna(subset=[mobile_column, company_column])  # Remove rows with empty values
            df[mobile_column] = df[mobile_column].astype(str).str.replace(r'\D', '', regex=True)  # Clean phone numbers
            df[company_column] = df[company_column].astype(str).str.strip()  # Clean company codes
            
            # Process in transaction
            with transaction.atomic():
                results = {
                    'companies_processed': set(),
                    'students_selected': 0,
                    'records_created': 0,
                    'records_updated': 0,
                    'students_rejected': 0,
                    'numbers_not_found': 0,
                    'invalid_companies': set(),
                    'processed_count': len(df)
                }
                
                # First pass: Process all selected students
                for _, row in df.iterrows():
                    mobile = row[mobile_column]
                    company_code = row[company_column]
                    
                    if not mobile or not company_code:
                        continue
                    
                    try:
                        # Get requirement
                        try:
                            requirement = Requirement.objects.get(company_code=company_code)
                            results['companies_processed'].add(company_code)
                        except ObjectDoesNotExist:
                            results['invalid_companies'].add(company_code)
                            continue
                        
                        # Find student
                        try:
                            student = Student.objects.get(contact_number=mobile)
                        except ObjectDoesNotExist:
                            results['numbers_not_found'] += 1
                            continue
                            
                        # Update or create record
                        obj, created = RequirementStudent.objects.update_or_create(
                            student=student,
                            requirement=requirement,
                            defaults={'status': 'selected'}
                        )
                        
                        if created:
                            results['records_created'] += 1
                            results['students_selected'] += 1
                        else:
                            if obj.status != 'selected':
                                obj.status = 'selected'
                                obj.save()
                                results['records_updated'] += 1
                                results['students_selected'] += 1
                            
                        # Update student counts
                        student.update_requirement_counts()
                        
                    except Exception as e:
                        continue
                
                # Second pass: Reject non-selected students for each company
                for company_code in results['companies_processed']:
                    try:
                        requirement = Requirement.objects.get(company_code=company_code)
                        selected_students = Student.objects.filter(
                            requirementstudent__requirement=requirement,
                            requirementstudent__status='selected'
                        )
                        
                        rejected = RequirementStudent.objects.filter(
                            requirement=requirement,
                            status='pending'  # Only reject pending status students
                        ).exclude(
                            student__in=selected_students
                        ).update(status='rejected')
                        
                        results['students_rejected'] += rejected
                    except Exception as e:
                        continue
                
                # Prepare results message
                msg = [
                    f"<strong>Processed {len(df)} rows</strong>",
                    f"<strong>Companies processed:</strong> {len(results['companies_processed'])}",
                    f"<strong>Students selected:</strong> {results['students_selected']}",
                    f"<strong>New records created:</strong> {results['records_created']}",
                    f"<strong>Existing records updated:</strong> {results['records_updated']}",
                    f"<strong>Students marked as rejected:</strong> {results['students_rejected']}",
                    f"<strong>Phone numbers not found:</strong> {results['numbers_not_found']}",
                ]
                
                if results['invalid_companies']:
                    sample = ", ".join(list(results['invalid_companies'])[:3])
                    msg.append(
                        f"<strong>Invalid company codes ({len(results['invalid_companies'])}):</strong> {sample}{'...' if len(results['invalid_companies']) > 3 else ''}"
                    )
                
                messages.success(request, "<br>".join(msg))
                context.update(results)
                
        except Exception as e:
            messages.error(request, f"<strong>Error:</strong> {str(e)}")
    
    return render(request, 'update_selected_students.html', context)

from django.views.generic import CreateView
from django.urls import reverse_lazy
from .models import Student
from django.contrib import messages
class StudentCreateView(CreateView):
    model = Student
    fields = [
        'name', 'contact_number', 'degree', 'stream', 'yop',
        'tenth_percent', 'twelfth_percent', 'degree_percent',
        'gender', 'type_of_data'
    ]
    template_name = 'student_add.html'
    success_url = reverse_lazy('student_data:add')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Student added successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

from django.http import HttpResponse
import openpyxl
from openpyxl.styles import Protection

def download_template(request):
    # Create a new workbook
    wb = openpyxl.Workbook()
    ws = wb.active
    
    # Add headers
    headers = [
        "S.No", 
        "Company Name", 
        "Company Code", 
        "Requirement Date (DD-MM-YYYY)", 
        "Schedule Date (DD-MM-YYYY)"
    ]
    ws.append(headers)
    
    # Add sample data
    sample_data = [
        ["1", "ABC Corp", "ABC001", "15-01-2025", "20-01-2025"],
        ["2", "XYZ Ltd", "XYZ002", "10-02-2025", ""],
    ]
    for row in sample_data:
        ws.append(row)
    
    # Format date columns as text to prevent Excel auto-formatting
    for cell in ws['D'] + ws['E']:
        cell.protection = Protection(locked=False)
        if cell.row > 1:  # Skip header
            cell.number_format = '@'  # Text format
    
    # Create response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="requirements_template.xlsx"'
    
    # Save workbook to response
    wb.save(response)
    return response