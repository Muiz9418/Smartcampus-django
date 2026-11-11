from django.urls import path
from . import views

urlpatterns = [
    path("create/", views.create_course, name="create_course"),
    path("my-courses/", views.my_courses, name="my_courses"),
    path("browse/", views.browse_courses, name="browse_courses"),
    path("enroll/<int:course_id>/", views.enroll_course, name="enroll_course"),
    path("my-enrollments/", views.my_enrollments, name="my_enrollments"),
    path("attendance/<int:course_id>/", views.mark_attendance, name="mark_attendance"),
    path("grades/<int:course_id>/", views.enter_grades, name="enter_grades"),
    path("my-attendance/<int:course_id>/", views.my_attendance, name="my_attendance"),
    path("my-grades/", views.my_grades, name="my_grades"),
    path("detail/<int:course_id>/", views.course_detail, name="course_detail"),
    path("student-detail/<int:course_id>/", views.student_course_detail, name="student_course_detail"),
    path("announce/<int:course_id>/", views.post_announcement, name="post_announcement"),
    path("notifications/", views.my_notifications, name="my_notifications"),
    # path("broadcast/", views.broadcast_message, name="broadcast_message"),
]
