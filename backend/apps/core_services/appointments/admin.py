from django.contrib import admin

# Register your models here.

from .models import Appointment, AppointmentChat

admin.site.register(Appointment)
admin.site.register(AppointmentChat)
