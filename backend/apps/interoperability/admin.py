from django.contrib import admin
from .models import FHIRServerConfig, PACSConfig, InteropAuditLog


@admin.register(FHIRServerConfig)
class FHIRServerConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'fhir_version', 'auth_type', 'is_active', 'updated_at')
    list_filter = ('is_active', 'fhir_version', 'auth_type')
    search_fields = ('name', 'base_url')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(PACSConfig)
class PACSConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'base_url', 'ae_title', 'auth_type', 'is_active', 'updated_at')
    list_filter = ('is_active', 'auth_type')
    search_fields = ('name', 'base_url', 'ae_title')
    readonly_fields = ('id', 'created_at', 'updated_at')
    fieldsets = (
        ('Thông tin chung', {
            'fields': ('name', 'base_url', 'ae_title', 'is_active'),
        }),
        ('Xác thực', {
            'fields': ('auth_type', 'auth_token'),
            'classes': ('collapse',),
        }),
        ('DICOMweb Paths', {
            'fields': ('wado_rs_path', 'stow_rs_path', 'qido_rs_path'),
        }),
        ('Cấu hình', {
            'fields': ('timeout_seconds',),
        }),
    )


@admin.register(InteropAuditLog)
class InteropAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'timestamp', 'direction', 'protocol',
        'resource_type', 'status', 'duration_ms',
    )
    list_filter = ('protocol', 'direction', 'status', 'resource_type')
    search_fields = ('resource_id', 'error_message')
    readonly_fields = (
        'timestamp', 'direction', 'protocol', 'resource_type',
        'resource_id', 'status', 'remote_server',
        'request_payload_size', 'response_payload_size',
        'duration_ms', 'error_message', 'initiated_by',
    )
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
