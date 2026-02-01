from django.contrib import admin
from .models import ServiceStation, QueueNumber, QueueEntry


@admin.register(ServiceStation)
class ServiceStationAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'station_type', 'is_active', 'current_staff']
    list_filter = ['station_type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(QueueNumber)
class QueueNumberAdmin(admin.ModelAdmin):
    list_display = ['number_code', 'visit', 'station', 'daily_sequence', 'created_date']
    list_filter = ['station', 'created_date']
    search_fields = ['number_code']
    date_hierarchy = 'created_date'


@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = ['queue_number', 'station', 'status', 'priority', 'entered_queue_time']
    list_filter = ['status', 'station', 'entered_queue_time']
    search_fields = ['queue_number__number_code']
