from datetime import timedelta

import anthropic
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from rest_framework import status, generics
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import AttendanceSession, AttendanceRecord, EnergyReading
from core.models import CourseMaterial, Course, Enrollment, Grade
from .serializers import (
    UserSerializer,
    SignupSerializer,
    AttendanceSessionSerializer,
    AttendanceRecordSerializer,
    CourseMaterialSerializer,
    EnergyReadingSerializer,
    GradeSerializer,
    GPA_POINTS,
)

User = get_user_model()

# Signs attendance codes so they can't be forged, and carries an expiry check.
# SECRET_KEY is your existing Django secret — no new config needed.
from django.conf import settings

_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="attendance-session")
SESSION_LIFETIME_SECONDS = 90  # a little longer than the app's 60s refresh, for clock drift


# ---------- AUTH ----------

@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email")
    password = request.data.get("password")
    if not email or not password:
        return Response({"message": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)

    # Your User model logs in via `username` (Django's AbstractUser default), but the
    # app sends email — so look up the username first, then authenticate with it.
    try:
        matched_user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    except User.MultipleObjectsReturned:
        # email isn't unique on AbstractUser by default — consider adding
        # unique=True to email on your User model to prevent this
        return Response({"message": "Multiple accounts share this email. Contact admin."}, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(request, username=matched_user.username, password=password)
    if user is None:
        return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data})


@api_view(["POST"])
@permission_classes([AllowAny])
def signup_view(request):
    serializer = SignupSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    user = serializer.save()
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": UserSerializer(user).data}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    request.user.auth_token.delete()
    return Response({"message": "Logged out."})


# ---------- ATTENDANCE ----------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_attendance_session(request):
    # ADJUST: swap "lecturer" for whatever your role field's value actually is
    if getattr(request.user, "role", None) != "lecturer":
        return Response({"message": "Only lecturers can start an attendance session."}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.data.get("course_id")
    course_name = request.data.get("course_name", course_id)
    if not course_id:
        return Response({"message": "course_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    payload = {"course_id": course_id, "lecturer_id": request.user.id}
    signed_code = _signer.dumps(payload)

    session = AttendanceSession.objects.create(
        lecturer=request.user,
        course_id=course_id,
        course_name=course_name,
        code=signed_code,
        expires_at=timezone.now() + timedelta(seconds=SESSION_LIFETIME_SECONDS),
    )
    return Response(AttendanceSessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_attendance(request):
    # ADJUST: swap "student" for your actual role value
    if getattr(request.user, "role", None) != "student":
        return Response({"message": "Only students can mark attendance."}, status=status.HTTP_403_FORBIDDEN)

    session_code = request.data.get("session_code")
    if not session_code:
        return Response({"message": "session_code is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        _signer.loads(session_code, max_age=SESSION_LIFETIME_SECONDS)
    except SignatureExpired:
        return Response({"message": "This code has expired. Ask your lecturer to refresh it."}, status=status.HTTP_400_BAD_REQUEST)
    except BadSignature:
        return Response({"message": "Invalid attendance code."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = AttendanceSession.objects.get(code=session_code)
    except AttendanceSession.DoesNotExist:
        return Response({"message": "Session not found."}, status=status.HTTP_404_NOT_FOUND)

    record, created = AttendanceRecord.objects.get_or_create(student=request.user, session=session)
    if not created:
        return Response({"message": "You've already marked attendance for this session."}, status=status.HTTP_400_BAD_REQUEST)

    return Response(
        {
            "status": "marked",
            "course": session.course_name,
            "timestamp": record.marked_at.strftime("%b %d, %Y %I:%M %p"),
        }
    )


class AttendanceHistoryView(generics.ListAPIView):
    serializer_class = AttendanceRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AttendanceRecord.objects.filter(student=self.request.user).order_by("-marked_at")


# ---------- MATERIALS ----------

class MaterialListView(generics.ListAPIView):
    """
    Students see materials only for courses they're enrolled in.
    Lecturers see materials for courses they teach.
    Admins see everything.
    """

    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = CourseMaterial.objects.select_related("course").order_by("-uploaded_at")

        if user.role == "student":
            enrolled_course_ids = Enrollment.objects.filter(student=user).values_list("course_id", flat=True)
            return base.filter(course_id__in=enrolled_course_ids)
        elif user.role == "lecturer":
            return base.filter(course__lecturer=user)
        return base  # admin sees all

    def get_serializer_context(self):
        return {"request": self.request}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_material(request):
    if getattr(request.user, "role", None) != "lecturer":
        return Response({"message": "Only lecturers can upload materials."}, status=status.HTTP_403_FORBIDDEN)

    course_id = request.data.get("course")
    try:
        course = Course.objects.get(id=course_id, lecturer=request.user)
    except Course.DoesNotExist:
        return Response({"message": "Course not found or you don't teach it."}, status=status.HTTP_404_NOT_FOUND)

    serializer = CourseMaterialSerializer(data=request.data, context={"request": request})
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(course=course)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ---------- AI ASSISTANT ----------

ASSISTANT_SYSTEM_PROMPT = (
    "You are Academia AI, a helpful academic assistant inside the EduSmart Campus app. "
    "You help students with study planning, understanding course concepts, and questions "
    "about their schedule. Keep answers concise and encouraging. If asked something outside "
    "an academic context, gently redirect to campus-related topics."
)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assistant_chat(request):
    from django.conf import settings

    if not getattr(settings, "ANTHROPIC_API_KEY", None):
        return Response(
            {"message": "AI assistant isn't configured yet — missing ANTHROPIC_API_KEY."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    message = request.data.get("message")
    history = request.data.get("history", [])  # [{role: "user"|"assistant", content: str}]

    if not message:
        return Response({"message": "message is required."}, status=status.HTTP_400_BAD_REQUEST)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build message history for the API — cap it so a long chat doesn't balloon token usage
    api_messages = [{"role": m["role"], "content": m["content"]} for m in history[-10:]]
    api_messages.append({"role": "user", "content": message})

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",  # cost-efficient — good fit for limited hackathon credits
            max_tokens=500,
            system=ASSISTANT_SYSTEM_PROMPT,
            messages=api_messages,
        )
        reply_text = "".join(block.text for block in response.content if block.type == "text")
    except anthropic.APIError as e:
        return Response({"message": f"AI service error: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

    return Response({"reply": reply_text})


# ---------- ENERGY MANAGEMENT ----------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_energy_reading(request):
    """Admin/facilities staff manually log a day's meter reading."""
    if getattr(request.user, "role", None) != "admin":
        return Response({"message": "Only admins can log energy readings."}, status=status.HTTP_403_FORBIDDEN)

    serializer = EnergyReadingSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    serializer.save(logged_by=request.user)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def energy_summary(request):
    """
    Real calculation off real (manually logged) readings — the last 7 entries.
    Returns nothing fabricated: if no readings exist yet, trend is empty and the
    frontend should show an honest "no data yet" state rather than a fake chart.
    """
    readings = EnergyReading.objects.order_by("-reading_date")[:7]
    readings = list(reversed(readings))  # oldest to newest for the chart

    if not readings:
        return Response({"savings_pct": 0, "current_kwh": 0, "trend": [], "message": "No readings logged yet."})

    latest = readings[-1]
    savings_pct = 0
    if latest.target_kwh and latest.target_kwh > 0:
        savings_pct = round(float((latest.target_kwh - latest.kwh_consumed) / latest.target_kwh) * 100, 1)

    return Response(
        {
            "savings_pct": savings_pct,
            "current_kwh": float(latest.kwh_consumed),
            "target_kwh": float(latest.target_kwh),
            "trend": [float(r.kwh_consumed) for r in readings],
        }
    )


# ---------- ACADEMIC PERFORMANCE ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def academic_performance(request):
    """
    Returns cumulative GPA + per-course grades for the logged-in student,
    plus a real credit-weighted GPA and a per-semester breakdown now that
    Course.credit_hours and Enrollment.semester exist.
    Enrollments without a semester set fall under "Unspecified" so old data
    doesn't disappear from the response.
    """
    if getattr(request.user, "role", None) != "student":
        return Response({"message": "Only students have academic performance records."}, status=status.HTTP_403_FORBIDDEN)

    grades = Grade.objects.filter(enrollment__student=request.user).select_related("enrollment__course")

    if not grades.exists():
        return Response({"cumulative_gpa": 0, "courses": [], "semesters": [], "message": "No grades recorded yet."})

    # Credit-weighted cumulative GPA: sum(gpa_points * credit_hours) / sum(credit_hours)
    total_points = 0.0
    total_credits = 0
    semester_map = {}  # semester label -> { points, credits }

    for g in grades:
        credit_hours = g.enrollment.course.credit_hours or 0
        gpa_points = GPA_POINTS.get(g.letter_grade, 0.0)
        total_points += gpa_points * credit_hours
        total_credits += credit_hours

        label = g.enrollment.semester or "Unspecified"
        bucket = semester_map.setdefault(label, {"points": 0.0, "credits": 0})
        bucket["points"] += gpa_points * credit_hours
        bucket["credits"] += credit_hours

    cumulative_gpa = round(total_points / total_credits, 2) if total_credits else 0

    semesters = [
        {
            "semester": label,
            "gpa": round(bucket["points"] / bucket["credits"], 2) if bucket["credits"] else 0,
            "credit_hours": bucket["credits"],
        }
        for label, bucket in semester_map.items()
    ]

    return Response(
        {
            "cumulative_gpa": cumulative_gpa,
            "courses": GradeSerializer(grades, many=True).data,
            "semesters": semesters,
        }
    )


# ---------- GRADE ENTRY ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def course_roster(request, course_id):
    """
    Returns the enrolled students for a course the requesting lecturer teaches,
    along with any existing grade for each — used to populate the grade-entry
    screen with current values.
    """
    if getattr(request.user, "role", None) != "lecturer":
        return Response({"message": "Only lecturers can view a course roster."}, status=status.HTTP_403_FORBIDDEN)

    try:
        course = Course.objects.get(id=course_id, lecturer=request.user)
    except Course.DoesNotExist:
        return Response({"message": "Course not found or you don't teach it."}, status=status.HTTP_404_NOT_FOUND)

    enrollments = Enrollment.objects.filter(course=course).select_related("student")
    roster = []
    for e in enrollments:
        grade = getattr(e, "grade", None)
        roster.append({
            "enrollment_id": e.id,
            "student_name": e.student.get_full_name() or e.student.username,
            "matric_number": getattr(e.student, "matric_number", None),
            "ca_score": grade.ca_score if grade else None,
            "exam_score": grade.exam_score if grade else None,
        })
    return Response({"course_code": course.code, "course_title": course.title, "roster": roster})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def enter_grades_api(request, course_id):
    """
    Saves CA/exam scores for one or more enrollments in a course the requesting
    lecturer teaches. Expects: { "grades": [{ "enrollment_id": 1, "ca_score": 25, "exam_score": 60 }, ...] }
    Reuses the same update_or_create pattern as the original core/views.py enter_grades
    view, just exposed as JSON instead of an HTML form.
    """
    if getattr(request.user, "role", None) != "lecturer":
        return Response({"message": "Only lecturers can enter grades."}, status=status.HTTP_403_FORBIDDEN)

    try:
        course = Course.objects.get(id=course_id, lecturer=request.user)
    except Course.DoesNotExist:
        return Response({"message": "Course not found or you don't teach it."}, status=status.HTTP_404_NOT_FOUND)

    grades_payload = request.data.get("grades", [])
    if not grades_payload:
        return Response({"message": "No grades provided."}, status=status.HTTP_400_BAD_REQUEST)

    saved = 0
    errors = []
    for entry in grades_payload:
        enrollment_id = entry.get("enrollment_id")
        try:
            enrollment = Enrollment.objects.get(id=enrollment_id, course=course)
        except Enrollment.DoesNotExist:
            errors.append({"enrollment_id": enrollment_id, "message": "Not enrolled in this course."})
            continue

        ca = entry.get("ca_score")
        exam = entry.get("exam_score")
        Grade.objects.update_or_create(
            enrollment=enrollment,
            defaults={"ca_score": ca or 0, "exam_score": exam or 0},
        )
        saved += 1

    return Response({"message": f"Saved {saved} grade(s) for {course.code}", "saved": saved, "errors": errors})


# ---------- LECTURER COURSE LIST ----------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_courses(request):
    """
    Returns the courses the requesting lecturer teaches, with a real enrolled-
    student count per course. No "progress %" field — nothing in the schema
    tracks syllabus/topic completion, so that's left out rather than faked.
    """
    if getattr(request.user, "role", None) != "lecturer":
        return Response({"message": "Only lecturers can view their course list."}, status=status.HTTP_403_FORBIDDEN)

    courses = Course.objects.filter(lecturer=request.user)
    data = [
        {
            "id": c.id,
            "code": c.code,
            "title": c.title,
            "credit_hours": c.credit_hours,
            "student_count": c.enrollments.count(),
        }
        for c in courses
    ]
    return Response({"courses": data})
