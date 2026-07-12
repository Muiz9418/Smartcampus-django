from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("register/", views.register_view, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("lecturer/", views.lecturer_dashboard, name="lecturer_dashboard"),
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("admin/verify/<int:user_id>/", views.toggle_verify, name="toggle_verify"),
    path("broadcast/", views.broadcast_message, name="broadcast_message"),
    path("profile/", views.profile_edit, name="profile_edit"),

    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html"), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"), name="password_reset_complete"),
]
