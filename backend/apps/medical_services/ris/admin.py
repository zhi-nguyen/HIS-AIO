from django.contrib import admin
from .models import Modality, ImagingProcedure, ImagingOrder, ImagingExecution, ImagingResult


@admin.register(Modality)
class ModalityAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'room_location', 'base_price', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code', 'name']


@admin.register(ImagingProcedure)
class ImagingProcedureAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'modality', 'body_part', 'price']
    list_filter = ['modality']
    search_fields = ['code', 'name', 'body_part']


@admin.register(ImagingOrder)
class ImagingOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'procedure', 'patient', 'status', 'priority', 'order_time']
    list_filter = ['status', 'priority', 'procedure__modality']
    search_fields = ['patient__fullname', 'visit__visit_code']
    date_hierarchy = 'order_time'


@admin.register(ImagingExecution)
class ImagingExecutionAdmin(admin.ModelAdmin):
    list_display = ['order', 'technician', 'execution_time', 'machine_id']
    search_fields = ['order__visit__visit_code', 'dicom_study_uid']


@admin.register(ImagingResult)
class ImagingResultAdmin(admin.ModelAdmin):
    list_display = ['order', 'radiologist', 'report_time', 'is_verified', 'is_abnormal', 'is_critical']
    list_filter = ['is_verified', 'is_abnormal', 'is_critical']
    search_fields = ['order__visit__visit_code', 'conclusion']
