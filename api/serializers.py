from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import AttendanceSession, AttendanceRecord, EnergyReading
from core.models import CourseMaterial, Grade

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "full_name", "first_name", "last_name",
            "email", "role", "matric_number", "department", "is_verified",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "username", "first_name", "last_name", "email", "password",
            "role", "matric_number", "department",
        ]
        extra_kwargs = {
            "matric_number": {"required": False},
            "department": {"required": False},
        }

    def validate(self, data):
        # Students should have a matric number; lecturers/admins generally won't.
        if data.get("role") == "student" and not data.get("matric_number"):
            raise serializers.ValidationError({"matric_number": "Required for student accounts."})
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AttendanceSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceSession
        fields = ["id", "course_id", "course_name", "code", "created_at", "expires_at"]
        read_only_fields = ["id", "code", "created_at", "expires_at"]


class AttendanceRecordSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="session.course_name", read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = ["id", "course_name", "marked_at"]


class CourseMaterialSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="course.code", read_only=True)
    course_title = serializers.CharField(source="course.title", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = CourseMaterial
        fields = ["id", "title", "description", "file", "file_url", "course", "course_code", "course_title", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]
        extra_kwargs = {"file": {"write_only": True}}  # accepted on upload, but read back via file_url instead

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None


class EnergyReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnergyReading
        fields = ["id", "reading_date", "kwh_consumed", "target_kwh", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


# Standard 4.0-scale mapping off your existing letter_grade property.
# NOTE: this is an unweighted average — your Course model has no credit_hours
# field yet, so this can't do a proper credit-weighted GPA until that's added.
GPA_POINTS = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}


class GradeSerializer(serializers.ModelSerializer):
    course_code = serializers.CharField(source="enrollment.course.code", read_only=True)
    course_title = serializers.CharField(source="enrollment.course.title", read_only=True)
    credit_hours = serializers.IntegerField(source="enrollment.course.credit_hours", read_only=True)
    semester = serializers.CharField(source="enrollment.semester", read_only=True)
    total = serializers.SerializerMethodField()
    letter_grade = serializers.CharField(read_only=True)
    gpa_points = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = [
            "id", "course_code", "course_title", "credit_hours", "semester", "ca_score", "exam_score",
            "total", "letter_grade", "gpa_points", "remarks", "graded_at",
        ]

    def get_total(self, obj):
        return float(obj.total)

    def get_gpa_points(self, obj):
        return GPA_POINTS.get(obj.letter_grade, 0.0)
