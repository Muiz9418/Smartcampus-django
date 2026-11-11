from django.conf import settings
from django.db import models


class AttendanceSession(models.Model):
    """
    Created by a lecturer when they start taking attendance for a class.
    The `code` is what actually goes into the QR — short-lived and signed,
    generated in views.py, not stored in plaintext meaning here.

    NOTE: course_id / course_name are plain fields so this drops in without
    depending on your existing Course model's exact location. Once you confirm
    where your Course model lives (e.g. `courses.models.Course`), swap these
    for a ForeignKey — it's a cleaner long-term shape.
    """

    lecturer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_sessions")
    course_id = models.CharField(max_length=50)
    course_name = models.CharField(max_length=200)
    code = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.course_name} — {self.created_at:%Y-%m-%d %H:%M}"


class AttendanceRecord(models.Model):
    """One student's confirmed attendance against a session."""

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance_records")
    session = models.ForeignKey(AttendanceSession, on_delete=models.CASCADE, related_name="records")
    marked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "session")  # one mark per student per session

    def __str__(self):
        return f"{self.student} — {self.session.course_name}"


class EnergyReading(models.Model):
    """
    A manually logged meter reading, entered by facilities/admin staff.
    This is the real, honest data source behind the Energy Management dashboard —
    there's no live IoT sensor feed, so this is where the numbers genuinely come from.
    """

    logged_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="energy_readings")
    reading_date = models.DateField()
    kwh_consumed = models.DecimalField(max_digits=10, decimal_places=2)
    target_kwh = models.DecimalField(max_digits=10, decimal_places=2, help_text="Baseline/target consumption for comparison")
    notes = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reading_date"]
        unique_together = ("reading_date",)  # one reading per day keeps the trend chart clean

    def __str__(self):
        return f"{self.reading_date} — {self.kwh_consumed} kWh"
