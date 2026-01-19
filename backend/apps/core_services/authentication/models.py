from django.db import models
from django.contrib.auth.models import AbstractUser
from uuid6 import uuid7

class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
        unique=True,
    )

    email = models.EmailField(unique=True, null=False, blank=False)
    phone = models.CharField(max_length=12, unique=True,null=False, blank=False)

    otp = models.CharField(max_length=6, null=True, blank=True)
    passcode = models.CharField(max_length=6, null=True, blank=True)

    passcode_created_at = models.DateTimeField(null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True)

    locked_until = models.DateTimeField(null=True, blank=True)
    rate_limit = models.IntegerField(default=0)
    request_limit = models.IntegerField(default=100)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

class Profile(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
        unique=True,
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

class Staff(models.Model):
    class StaffRole(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrator'
        DOCTOR = "DOCTOR", 'Doctor'
        NURSE = "NURSE", 'Nurse'
        RECEPTIONIST = "RECEPTIONIST", 'Receptionist'
        LAB_TECHNICIAN = "LAB_TECHNICIAN", 'Lab Technician'
        PHARMACIST = "PHARMACIST", 'Pharmacist'
        AI_AGENT = "AI_AGENT", 'AI Agent'

    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
        unique=True,
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=StaffRole.choices)
    department = models.CharField(max_length=100)
    hire_date = models.DateField()

class Certification(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid7,
        editable=False,
        unique=True,
    )
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='certifications')
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    issued_by = models.CharField(max_length=255)
    issue_date = models.DateField()
    expiration_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} issued by {self.issued_by} to {self.staff.user.username}"
    


