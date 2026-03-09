from django.contrib import admin

# Register your models here.

from .models import Department, DepartmentMember

admin.site.register(Department)
admin.site.register(DepartmentMember)
