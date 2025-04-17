from django import forms
from .models import Requirement


class BaseRequirementForm(forms.ModelForm):
    is_scheduled = forms.TypedChoiceField(
        required=False,
        choices=[(0, 'No'), (1, 'Yes')],
        coerce=lambda x: bool(int(x)),
        widget=forms.RadioSelect,
        label="Is Scheduled"
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

        if is_scheduled and not schedule_date:
            self.add_error('schedule_date', 'Schedule date is required when the requirement is scheduled.')

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


class RequirementEditForm(BaseRequirementForm):
    pass
