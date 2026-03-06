from django.contrib import admin

from apps.medical_services.pharmacy.models import (
    DrugCategory, Medication, MedicationLot,
    Prescription, PrescriptionDetail, DispenseRecord,
)
from apps.medical_services.pharmacy.drug_interactions import DrugInteraction
from apps.medical_services.emr.guidelines import ClinicalGuideline


@admin.register(DrugCategory)
class DrugCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active')
    search_fields = ('name',)


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'active_ingredient', 'atc_code', 'dosage_form', 'inventory_count', 'is_active')
    search_fields = ('code', 'name', 'active_ingredient', 'national_drug_code', 'atc_code')
    list_filter = ('category', 'dosage_form', 'requires_prescription', 'is_active')
    fieldsets = (
        ('Thông tin cơ bản', {'fields': ('code', 'name', 'category', 'active_ingredient', 'strength', 'dosage_form', 'usage_route', 'unit')}),
        ('Chuẩn hóa danh mục (Track 1)', {'fields': ('national_drug_code', 'atc_code')}),
        ('Giá', {'fields': ('purchase_price', 'selling_price')}),
        ('Kho', {'fields': ('inventory_count', 'min_stock', 'requires_prescription', 'is_active')}),
    )


@admin.register(MedicationLot)
class MedicationLotAdmin(admin.ModelAdmin):
    list_display = ('medication', 'lot_number', 'expiry_date', 'remaining_quantity', 'is_active')
    search_fields = ('medication__name', 'lot_number')
    list_filter = ('is_active',)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('prescription_code', 'visit', 'doctor', 'status', 'prescription_date')
    search_fields = ('prescription_code',)
    list_filter = ('status',)
    readonly_fields = ('cdss_alerts',)


@admin.register(DrugInteraction)
class DrugInteractionAdmin(admin.ModelAdmin):
    """Admin cho cơ sở dữ liệu tương tác thuốc – CDSS Track 3."""
    list_display = ('drug_a_name', 'drug_b_name', 'severity', 'is_active')
    search_fields = ('drug_a_name', 'drug_b_name')
    list_filter = ('severity', 'is_active')
    readonly_fields = ('drug_a_name', 'drug_b_name')  # Normalized on save — show as readonly after initial entry
    fieldsets = (
        ('Cặp thuốc tương tác', {'fields': ('drug_a_name', 'drug_b_name', 'severity', 'is_active')}),
        ('Thông tin lâm sàng', {'fields': ('description', 'recommendation', 'references')}),
    )


@admin.register(ClinicalGuideline)
class ClinicalGuidelineAdmin(admin.ModelAdmin):
    """Admin cho phác đồ điều trị – RAG Track 2."""
    list_display = ('title', 'source', 'version', 'effective_date', 'is_active')
    search_fields = ('title', 'source')
    list_filter = ('is_active', 'source')
    filter_horizontal = ('icd10_codes',)
    fieldsets = (
        ('Thông tin phác đồ', {'fields': ('title', 'version', 'source', 'effective_date', 'is_active')}),
        ('ICD-10 liên quan', {'fields': ('icd10_codes',)}),
        ('Nội dung', {'fields': ('content',)}),
    )
