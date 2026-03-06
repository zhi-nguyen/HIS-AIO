from django.contrib import admin
from apps.core_services.core.models import (
    Province, Ward,
    ICD10Category, ICD10Subcategory, ICD10Code,
    ICD11Code, TechnicalService,
)


@admin.register(ICD10Category)
class ICD10CategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')


@admin.register(ICD10Subcategory)
class ICD10SubcategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category')
    search_fields = ('code', 'name')
    list_filter = ('category',)


@admin.register(ICD10Code)
class ICD10CodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'subcategory')
    search_fields = ('code', 'name')


@admin.register(ICD11Code)
class ICD11CodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'is_billable', 'is_active')
    search_fields = ('code', 'title', 'title_vi')
    list_filter = ('is_billable', 'is_active')
    filter_horizontal = ('icd10_map',)


@admin.register(TechnicalService)
class TechnicalServiceAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'group', 'unit_price', 'bhyt_price', 'is_covered_by_bhyt', 'is_active')
    search_fields = ('code', 'name')
    list_filter = ('group', 'is_covered_by_bhyt', 'is_active')
