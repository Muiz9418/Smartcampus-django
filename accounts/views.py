from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.core.paginator import Paginator
from .decorators import role_required
from .forms import RegistrationForm, ProfileEditForm
from .models import User


def home_view(request):
    if request.user.is_authenticated:
        if request.user.role == "admin" or request.user.is_superuser:
            return redirect("admin_dashboard")
        if request.user.role == "lecturer":
            return redirect("lecturer_dashboard")
        return redirect("student_dashboard")
    return render(request, "accounts/home.html")


def register_view(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            if user.role == "lecturer":
                return redirect("lecturer_dashboard")
            return redirect("student_dashboard")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"

    def get_success_url(self):
        user = self.request.user
        if user.role == "admin" or user.is_superuser:
            return "/accounts/admin/"
        if user.role == "lecturer":
            return "/accounts/lecturer/"
        return "/accounts/student/"


def logout_view(request):
    logout(request)
    return redirect("login")


@role_required("student")
def student_dashboard(request):
    from core.models import Enrollment, Attendance
    enrollments = Enrollment.objects.filter(student=request.user)
    course_count = enrollments.count()

    total_records = 0
    present_records = 0
    for e in enrollments:
        records = Attendance.objects.filter(enrollment=e)
        total_records += records.count()
        present_records += records.filter(present=True).count()
    attendance_rate = round((present_records / total_records) * 100, 1) if total_records else 0
    graded_count = sum(1 for e in enrollments if hasattr(e, "grade"))

    return render(request, "accounts/student_dashboard.html", {
        "enrollments": enrollments,
        "course_count": course_count,
        "attendance_rate": attendance_rate,
        "graded_count": graded_count,
    })


@role_required("lecturer", "admin")
def lecturer_dashboard(request):
    from core.models import Course, Enrollment
    courses = Course.objects.filter(lecturer=request.user)
    student_total = Enrollment.objects.filter(course__in=courses).count()
    return render(request, "accounts/lecturer_dashboard.html", {
        "courses": courses,
        "course_count": courses.count(),
        "student_total": student_total,
    })


@role_required("admin")
def admin_dashboard(request):
    from core.models import Course, Enrollment
    students_qs = User.objects.filter(role="student")
    lecturers_qs = User.objects.filter(role="lecturer")
    courses_qs = Course.objects.all()

    student_paginator = Paginator(students_qs, 5)
    lecturer_paginator = Paginator(lecturers_qs, 5)
    course_paginator = Paginator(courses_qs, 5)

    students = student_paginator.get_page(request.GET.get("student_page"))
    lecturers = lecturer_paginator.get_page(request.GET.get("lecturer_page"))
    courses = course_paginator.get_page(request.GET.get("course_page"))

    return render(request, "accounts/admin_dashboard.html", {
        "students": students,
        "lecturers": lecturers,
        "courses": courses,
        "student_count": students_qs.count(),
        "lecturer_count": lecturers_qs.count(),
        "course_count": courses_qs.count(),
        "enrollment_count": Enrollment.objects.count(),
    })


@role_required("admin")
def toggle_verify(request, user_id):
    target = User.objects.get(id=user_id)
    target.is_verified = not target.is_verified
    target.save()
    return redirect("admin_dashboard")


@role_required("admin")
def broadcast_message(request):
    from core.models import Notification
    if request.method == "POST":
        message = request.POST.get("message")
        target = request.POST.get("target")
        if target == "students":
            recipients = User.objects.filter(role="student")
        elif target == "lecturers":
            recipients = User.objects.filter(role="lecturer")
        else:
            recipients = User.objects.exclude(role="admin")

        for user in recipients:
            Notification.objects.create(recipient=user, course=None, message=message)

        messages.success(request, f"Broadcast sent to {recipients.count()} user(s)")
        return redirect("admin_dashboard")

    return render(request, "accounts/broadcast.html")


@role_required("student", "lecturer")
def profile_edit(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated")
            if request.user.role == "lecturer":
                return redirect("lecturer_dashboard")
            return redirect("student_dashboard")
    else:
        form = ProfileEditForm(instance=request.user)
    return render(request, "accounts/profile_edit.html", {"form": form})
