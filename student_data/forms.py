from django import forms
from .models import Requirement

class RequirementForm(forms.ModelForm):
    student_file = forms.FileField(
        required=False,
        help_text="Upload an Excel file containing student mobile numbers"
    )
    
    mobile_column = forms.CharField(
        required=False,
        initial="mobile",
        help_text="Name of the column containing mobile numbers in the Excel file"
    )
    
    class Meta:
        model = Requirement
        fields = ['company_name', 'company_code', 'requirement_date', 'is_scheduled', 'schedule_date', 'description']
        widgets = {
            'requirement_date': forms.DateInput(attrs={'type': 'date'}),
            'schedule_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_scheduled = cleaned_data.get('is_scheduled')
        schedule_date = cleaned_data.get('schedule_date')
        
        if is_scheduled and not schedule_date:
            self.add_error('schedule_date', 'Schedule date is required when the requirement is scheduled.')
            
        return cleaned_data
class RequirementEditForm(forms.ModelForm):
    class Meta:
        model = Requirement
        fields = ['company_name', 'company_code', 'requirement_date', 'is_scheduled', 'schedule_date', 'description']
        widgets = {
            'requirement_date': forms.DateInput(attrs={'type': 'date'}),
            'schedule_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        is_scheduled = cleaned_data.get('is_scheduled')
        schedule_date = cleaned_data.get('schedule_date')
        
        if is_scheduled and not schedule_date:
            self.add_error('schedule_date', 'Schedule date is required when the requirement is scheduled.')
            
        return cleaned_data