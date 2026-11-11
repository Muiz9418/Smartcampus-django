from django.db import models
from django.conf import settings


class Course(models.Model):
    title = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_taught",
        limit_choices_to={"role": "lecturer"},
    )
    credit_hours = models.PositiveSmallIntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.title}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        limit_choices_to={"role": "student"},
    )
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    semester = models.CharField(max_length=50, blank=True, null=True)  # e.g. "Fall 2024"
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student.username} -> {self.course.code}"


class Attendance(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="attendance_records")
    date = models.DateField()
    present = models.BooleanField(default=False)

    class Meta:
        unique_together = ("enrollment", "date")

    def __str__(self):
        status = "Present" if self.present else "Absent"
        return f"{self.enrollment.student.username} - {self.date} - {status}"


class Grade(models.Model):
    enrollment = models.OneToOneField(Enrollment, on_delete=models.CASCADE, related_name="grade")
    ca_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    remarks = models.CharField(max_length=200, blank=True, null=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    @property
    def total(self):
        return self.ca_score + self.exam_score

    @property
    def letter_grade(self):
        t = self.total
        if t >= 70: return "A"
        if t >= 60: return "B"
        if t >= 50: return "C"
        if t >= 45: return "D"
        return "F"

    def __str__(self):
        return f"{self.enrollment.student.username} - {self.enrollment.course.code} - {self.total}"


class CourseMaterial(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="materials")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="course_materials/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Notification(models.Model):
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient.username}: {self.message[:30]}"
