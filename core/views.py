from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from accounts.decorators import role_required
from .models import Course, Enrollment, Attendance, Grade, CourseMaterial, Notification
from .forms import CourseForm, CourseMaterialForm, AnnouncementForm


@role_required("lecturer", "admin")
def create_course(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.lecturer = request.user
            course.save()
            return redirect("my_courses")
    else:
        form = CourseForm()
    return render(request, "core/create_course.html", {"form": form})


@role_required("lecturer", "admin")
def my_courses(request):
    courses = Course.objects.filter(lecturer=request.user)
    return render(request, "core/my_courses.html", {"courses": courses})


@role_required("student")
def browse_courses(request):
    enrolled_ids = Enrollment.objects.filter(student=request.user).values_list("course_id", flat=True)
    courses = Course.objects.exclude(id__in=enrolled_ids)
    return render(request, "core/browse_courses.html", {"courses": courses})


@role_required("student")
def enroll_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    Enrollment.objects.get_or_create(student=request.user, course=course)
    messages.success(request, f"Enrolled in {course.code}")
    return redirect("my_enrollments")


@role_required("student")
def my_enrollments(request):
    enrollments = Enrollment.objects.filter(student=request.user)
    return render(request, "core/my_enrollments.html", {"enrollments": enrollments})


@role_required("lecturer", "admin")
def mark_attendance(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    enrollments = Enrollment.objects.filter(course=course)
    today = date.today()

    if request.method == "POST":
        for enrollment in enrollments:
            present = request.POST.get(f"present_{enrollment.id}") == "on"
            Attendance.objects.update_or_create(
                enrollment=enrollment,
                date=today,
                defaults={"present": present},
            )
        messages.success(request, f"Attendance marked for {today}")
        return redirect("my_courses")

    return render(request, "core/mark_attendance.html", {
        "course": course,
        "enrollments": enrollments,
        "today": today,
    })


@role_required("lecturer", "admin")
def enter_grades(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    enrollments = Enrollment.objects.filter(course=course)

    if request.method == "POST":
        for enrollment in enrollments:
            ca = request.POST.get(f"ca_{enrollment.id}")
            exam = request.POST.get(f"exam_{enrollment.id}")
            if ca or exam:
                Grade.objects.update_or_create(
                    enrollment=enrollment,
                    defaults={"ca_score": ca or 0, "exam_score": exam or 0},
                )
        messages.success(request, f"Grades saved for {course.code}")
        return redirect("my_courses")

    grades = {g.enrollment_id: g for g in Grade.objects.filter(enrollment__course=course)}
    return render(request, "core/enter_grades.html", {
        "course": course,
        "enrollments": enrollments,
        "grades": grades,
    })


@role_required("student")
def my_attendance(request, course_id):
    enrollment = get_object_or_404(Enrollment, student=request.user, course_id=course_id)
    records = Attendance.objects.filter(enrollment=enrollment).order_by("-date")
    total = records.count()
    present_count = records.filter(present=True).count()
    percentage = round((present_count / total) * 100, 1) if total > 0 else 0
    return render(request, "core/my_attendance.html", {
        "enrollment": enrollment,
        "records": records,
        "percentage": percentage,
    })


@role_required("student")
def my_grades(request):
    enrollments = Enrollment.objects.filter(student=request.user)
    return render(request, "core/my_grades.html", {"enrollments": enrollments})


@role_required("lecturer", "admin")
def course_detail(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    materials = CourseMaterial.objects.filter(course=course).order_by("-uploaded_at")

    if request.method == "POST":
        form = CourseMaterialForm(request.POST, request.FILES)
        if form.is_valid():
            material = form.save(commit=False)
            material.course = course
            material.save()
            messages.success(request, "Material uploaded")
            return redirect("course_detail", course_id=course.id)
    else:
        form = CourseMaterialForm()

    return render(request, "core/course_detail.html", {
        "course": course,
        "materials": materials,
        "form": form,
    })


@role_required("student")
def student_course_detail(request, course_id):
    enrollment = get_object_or_404(Enrollment, student=request.user, course_id=course_id)
    materials = CourseMaterial.objects.filter(course=enrollment.course).order_by("-uploaded_at")
    return render(request, "core/student_course_detail.html", {
        "course": enrollment.course,
        "materials": materials,
    })


@role_required("lecturer", "admin")
def post_announcement(request, course_id):
    course = get_object_or_404(Course, id=course_id, lecturer=request.user)
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            msg = form.cleaned_data["message"]
            students = Enrollment.objects.filter(course=course)
            for e in students:
                Notification.objects.create(recipient=e.student, course=course, message=msg)
            messages.success(request, "Announcement sent")
            return redirect("course_detail", course_id=course.id)
    else:
        form = AnnouncementForm()
    return render(request, "core/post_announcement.html", {"course": course, "form": form})


@role_required("student","lecturer")
def my_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, "core/my_notifications.html", {"notifications": notifications})
