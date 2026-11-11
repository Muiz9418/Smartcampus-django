from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("auth/login/", views.login_view, name="api-login"),
    path("auth/signup/", views.signup_view, name="api-signup"),
    path("auth/logout/", views.logout_view, name="api-logout"),

    # Attendance
    path("attendance/sessions/", views.create_attendance_session, name="api-attendance-create"),
    path("attendance/mark/", views.mark_attendance, name="api-attendance-mark"),
    path("attendance/history/", views.AttendanceHistoryView.as_view(), name="api-attendance-history"),

    # Materials
    path("materials/", views.MaterialListView.as_view(), name="api-materials-list"),
    path("materials/upload/", views.upload_material, name="api-materials-upload"),

    # AI Assistant
    path("assistant/chat/", views.assistant_chat, name="api-assistant-chat"),

    # Energy Management
    path("energy/log/", views.log_energy_reading, name="api-energy-log"),
    path("energy/summary/", views.energy_summary, name="api-energy-summary"),

    # Academic Performance
    path("academics/performance/", views.academic_performance, name="api-academic-performance"),
    path("courses/mine/", views.my_courses, name="api-my-courses"),
    path("courses/<int:course_id>/roster/", views.course_roster, name="api-course-roster"),
    path("courses/<int:course_id>/grades/", views.enter_grades_api, name="api-enter-grades"),
]
