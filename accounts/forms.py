from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class RegistrationForm(UserCreationForm):
    ROLE_CHOICES = (
        ("student", "Student"),
        ("lecturer", "Lecturer"),
    )
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    matric_number = forms.CharField(max_length=20, required=False)
    department = forms.CharField(max_length=100, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "role", "matric_number", "department", "password1", "password2")

    def clean_matric_number(self):
        matric = self.cleaned_data.get("matric_number")
        return matric if matric else None


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("email", "matric_number", "department")

    def clean_matric_number(self):
        matric = self.cleaned_data.get("matric_number")
        return matric if matric else None
