from django.contrib import admin

# Register your models here.

from .models import User, Profile, Staff, Certification

admin.site.register(User)
admin.site.register(Profile)
admin.site.register(Staff)
admin.site.register(Certification)
