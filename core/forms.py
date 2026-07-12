from django import forms
from .models import Course, CourseMaterial


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["title", "code", "description"]


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial
        fields = ["title", "description", "file"]


class AnnouncementForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea, label="Announcement")
