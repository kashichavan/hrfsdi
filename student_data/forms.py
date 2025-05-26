from django import forms
from .models import *


class BaseRequirementForm(forms.ModelForm):
    is_scheduled = forms.TypedChoiceField(
        required=False,
        choices=[(0, 'No'), (1, 'Yes')],
        coerce=lambda x: bool(int(x)),
        widget=forms.RadioSelect,
        label="Is Scheduled"
    )
    subjects = forms.ModelMultipleChoiceField(
        queryset=Subject.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Subjects",
    )
    percentage_10th = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '10th Percentage'})
    )
    percentage_12th = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '12th Percentage'})
    )
    percentage_degree = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Degree Percentage'})
    )
    percentage_master = forms.FloatField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Master\'s Percentage'})
    )
    
    other_subject_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Specify other subject'}),
        label="Other Subject Name"
    )
    

    class Meta:
        model = Requirement
        fields = [
            'company_name',
            'company_code',
            'requirement_date',
            'is_scheduled',
            'schedule_date',
            'description',
            'subjects',
            'other_subject_name',
            'percentage_10th', 'percentage_12th', 'percentage_degree', 'percentage_master',
        ]
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'form-control'}),
            'company_code': forms.TextInput(attrs={'class': 'form-control'}),
            'requirement_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'schedule_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_scheduled = cleaned_data.get('is_scheduled')
        schedule_date = cleaned_data.get('schedule_date')
        subjects = cleaned_data.get('subjects')
        other_subject_name = cleaned_data.get('other_subject_name')

        if is_scheduled and not schedule_date:
            self.add_error('schedule_date', 'Schedule date is required when the requirement is scheduled.')

        if subjects and Subject.objects.filter(name='other').first() in subjects and not other_subject_name:
            self.add_error('other_subject_name', 'Please specify the other subject name.')

        return cleaned_data

class RequirementForm(BaseRequirementForm):
    student_file = forms.FileField(
        required=False,
        help_text="Upload an Excel file containing student mobile numbers",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    mobile_column = forms.CharField(
        required=False,
        initial="mobile",
        help_text="Name of the column containing mobile numbers in the Excel file",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )



class SubjectPercentageForm(forms.Form):
    subject = forms.ModelChoiceField(queryset=Subject.objects.all())
    percentage = forms.IntegerField(min_value=1, max_value=100, initial=100)

class RequirementEditForm(BaseRequirementForm):
    pass



# forms.py

# forms.py

from django import forms
from .models import Student, Subject, StudentSubjectRating

class StudentSubjectRatingForm(forms.ModelForm):
    class Meta:
        model = StudentSubjectRating
        fields = ['subject', 'rating', 'remarks']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'rating': forms.Select(choices=StudentSubjectRating.RATING_CHOICES, attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }

# Use formset factory to allow multiple subject ratings
StudentSubjectRatingFormSet = forms.inlineformset_factory(
    Student,
    StudentSubjectRating,
    form=StudentSubjectRatingForm,
    extra=1,
    can_delete=True
)


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        exclude = [
            'created_at', 
            'total_requirements', 
            'scheduled_requirements', 
            'is_placed',
            'overall_technical_rating'  # Removed this field
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'degree': forms.TextInput(attrs={'class': 'form-control'}),
            'stream': forms.TextInput(attrs={'class': 'form-control'}),
            'yop': forms.NumberInput(attrs={'class': 'form-control'}),
            'tenth_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'twelfth_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'degree_percent': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'type_of_data': forms.TextInput(attrs={'class': 'form-control'}),
            'dropout_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'dropout_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'is_dropout' in self.data:
            is_dropout = self.data.get('is_dropout') == 'on'
        else:
            is_dropout = self.instance.is_dropout if self.instance else False

        if not is_dropout:
            self.fields['dropout_date'].required = False
            self.fields['dropout_reason'].required = False
        else:
            self.fields['dropout_date'].required = True
            
    def clean_contact_number(self):
        contact_number = self.cleaned_data.get('contact_number')
        if Student.objects.filter(contact_number=contact_number).exists():
            raise forms.ValidationError("A student with this contact number already exists.")
        return contact_number
            
            
            
from django import forms
from .models import GotPlacedOutside, Student

from django import forms
from .models import GotPlacedOutside, Student


class GotPlacedOutsideForm(forms.ModelForm):
    class Meta:
        model = GotPlacedOutside
        fields = ['student', 'company_name', 'role', 'package', 'placed_date']
        widgets = {
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name',
            }),
            'role': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'E.g., Software Engineer',
            }),
            'package': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Annual package in LPA',
                'step': '0.01',
                'min': '0',
            }),
            'placed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'student': forms.Select(attrs={
                'class': 'form-select form-control',
                'aria-label': 'Select student',
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filter student queryset to only include unplaced students
        self.fields['student'].queryset = Student.objects.filter(is_placed=False)

        # Optional: Add help text or customize labels if needed
        self.fields['package'].help_text = "In Lakhs Per Annum (LPA)"
        self.fields['placed_date'].help_text = "Date when student was placed"


# forms.py
from django import forms
from django.core.validators import FileExtensionValidator

class BulkOutsidePlacementForm(forms.Form):
    excel_file = forms.FileField(
        label='Excel File',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])],
        help_text="Upload Excel file with columns: mobile_number, company_name, package, role, placed_date"
    )
    
    
# forms.py

from django import forms
from django.forms import inlineformset_factory
from .models import StudentSubjectRating, Subject

class StudentSubjectRatingForm(forms.ModelForm):
    class Meta:
        model = StudentSubjectRating
        fields = ['subject', 'rating', 'remarks', 'evaluated_by']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-control'}),
            'rating': forms.Select(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'evaluated_by': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        # Pop request if passed from view
        self.request = kwargs.pop('request', None)

        super().__init__(*args, **kwargs)

        # Only show active subjects
        self.fields['subject'].queryset = Subject.objects.filter(is_active=True)

        # Set default evaluated_by if available
        if not self.initial.get('evaluated_by') and self.request:
            user = self.request.user
            self.initial['evaluated_by'] = user.get_full_name() if user.is_authenticated else ''

# Create formset factory
StudentSubjectRatingFormSet = inlineformset_factory(
    parent_model=Student,
    model=StudentSubjectRating,
    form=StudentSubjectRatingForm,
    extra=1,
    can_delete=True
)

# forms.py
from django import forms
from django.core.validators import FileExtensionValidator

class BulkStudentRatingUploadForm(forms.Form):
    file = forms.FileField(
        label='Upload Excel/CSV File',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'csv'])],
        help_text="File format: MobileNo, Subject1, Subject1_Rating, Subject2, Subject2_Rating, ... (2-5 subjects)"
    )
    
from django import forms
from .models import StudentSubjectRating

class StudentSubjectRatingForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop('student', None)
        super().__init__(*args, **kwargs)
        if self.student:
            rated_subjects = StudentSubjectRating.objects.filter(
                student=self.student
            ).values_list('subject', flat=True)
            self.fields['subject'].queryset = Subject.objects.exclude(
                id__in=rated_subjects
            )

    class Meta:
        model = StudentSubjectRating
        fields = ['subject', 'rating', 'remarks']
        widgets = {
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }