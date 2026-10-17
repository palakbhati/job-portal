from django import forms
from .models import Job, Application

class Jobform(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['title', 'company_name','description','location','salary']


class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['resume', 'cover_letter']
        widgets = {
            'resume': forms.ClearableFileInput(attrs={'accept': '.pdf,.doc,.docx'}),
            'cover_letter': forms.Textarea(attrs={
                'placeholder': 'Tell the employer why you are a great fit for this role (optional).'
            }),
        }
        help_texts = {
            'resume': 'PDF, DOC or DOCX, up to 5 MB.',
        }
