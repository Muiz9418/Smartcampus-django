from django.contrib import admin
from .models import Course, Enrollment, Attendance, Grade

admin.site.register(Course)
admin.site.register(Enrollment)
admin.site.register(Attendance)
admin.site.register(Grade)