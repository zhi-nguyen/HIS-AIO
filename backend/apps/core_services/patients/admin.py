from django.contrib import admin
from apps.core_services.patients.models import Patient
from apps.core_services.patients.allergy import PatientAllergy


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('patient_code', 'full_name', 'gender', 'date_of_birth', 'contact_number', 'is_active')
    search_fields = ('patient_code', 'first_name', 'last_name', 'id_card', 'insurance_number')
    list_filter = ('gender', 'is_active')


@admin.register(PatientAllergy)
class PatientAllergyAdmin(admin.ModelAdmin):
    list_display = ('patient', 'allergen_name', 'allergen_type', 'severity', 'confirmed_date', 'is_active')
    list_filter = ('allergen_type', 'severity', 'is_active')
    search_fields = ('patient__patient_code', 'patient__last_name', 'allergen_name_normalized')
    autocomplete_fields = ['patient']
    readonly_fields = ('allergen_name_normalized',)
