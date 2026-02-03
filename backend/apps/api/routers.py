from rest_framework.routers import DefaultRouter

router = DefaultRouter()

from apps.core_services.patients.views import PatientViewSet
from apps.core_services.reception.views import VisitViewSet
from apps.core_services.qms.views import QueueNumberViewSet, ServiceStationViewSet

router.register(r'patients', PatientViewSet)
router.register(r'reception/visits', VisitViewSet)
router.register(r'qms/queues', QueueNumberViewSet)
router.register(r'qms/stations', ServiceStationViewSet)

from apps.medical_services.emr.views import ClinicalRecordViewSet
router.register(r'emr/records', ClinicalRecordViewSet)

# ... (Previous registrations)
from apps.core_services.billing.views import ServiceCatalogViewSet
router.register(r'billing/services', ServiceCatalogViewSet)

# Paraclinical & Pharmacy
from apps.medical_services.lis.views import LabOrderViewSet, LabTestViewSet
from apps.medical_services.ris.views import ImagingOrderViewSet, ImagingProcedureViewSet
from apps.medical_services.pharmacy.views import PrescriptionViewSet, MedicationViewSet

router.register(r'lis/orders', LabOrderViewSet)
router.register(r'lis/tests', LabTestViewSet)
router.register(r'ris/orders', ImagingOrderViewSet)
router.register(r'ris/procedures', ImagingProcedureViewSet)
router.register(r'pharmacy/prescriptions', PrescriptionViewSet)
router.register(r'pharmacy/medications', MedicationViewSet)




