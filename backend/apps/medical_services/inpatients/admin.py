from django.contrib import admin
from .models import Ward, Room, Bed, Admission, DailyCare, BedTransfer


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'department', 'total_beds', 'phone']
    search_fields = ['code', 'name']


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ['room_number', 'ward', 'room_type', 'total_beds', 'daily_rate']
    list_filter = ['room_type', 'ward']
    search_fields = ['room_number']


@admin.register(Bed)
class BedAdmin(admin.ModelAdmin):
    list_display = ['bed_number', 'room', 'status']
    list_filter = ['status', 'room__ward']


@admin.register(Admission)
class AdmissionAdmin(admin.ModelAdmin):
    list_display = ['admission_number', 'patient', 'bed', 'status', 'admission_time']
    list_filter = ['status']
    search_fields = ['admission_number', 'patient__fullname']
    date_hierarchy = 'admission_time'


@admin.register(DailyCare)
class DailyCareAdmin(admin.ModelAdmin):
    list_display = ['admission', 'care_date', 'attending_doctor']
    list_filter = ['care_date']
    search_fields = ['admission__patient__fullname']


@admin.register(BedTransfer)
class BedTransferAdmin(admin.ModelAdmin):
    list_display = ['admission', 'from_bed', 'to_bed', 'transfer_time']
    search_fields = ['admission__patient__fullname']
