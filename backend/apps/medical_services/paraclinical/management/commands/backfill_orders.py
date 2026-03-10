import os
from dotenv import load_dotenv

load_dotenv()
from django.core.management.base import BaseCommand

# Must load models AFTER dotenv if accessed globally, but management command loads django first.
from apps.medical_services.paraclinical.models import ServiceOrder
from apps.medical_services.lis.models import LabOrder, LabTest, LabOrderDetail

class Command(BaseCommand):
    help = 'Backfill LIS LabOrders from existing XN ServiceOrders'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting backfill for existing ServiceOrders (XN, LAB, Huyết học, Sinh hóa) -> LabOrder ...")

        orders = ServiceOrder.objects.filter(service__category__in=['XN', 'LAB', 'Huyết học', 'Sinh hóa'])
        created_count = 0
        tests_added_count = 0

        for o in orders:
            visit = o.visit
            requester = o.requester
            lab_order, created = LabOrder.objects.get_or_create(
                visit=visit, 
                defaults={
                    'patient': visit.patient, 
                    'doctor': requester, 
                    'status': 'PENDING'
                }
            )
            if created:
                created_count += 1
                
            svc_name_lower = o.service.name.lower()
            cat = o.service.category
            
            if cat in ['XN', 'LAB']:
                if 'máu' in svc_name_lower or 'cbc' in svc_name_lower or 'huyết' in svc_name_lower:
                    tests = LabTest.objects.filter(category__name__icontains='Huyết học')
                elif 'sinh hóa' in svc_name_lower or 'đường' in svc_name_lower or 'hba1c' in svc_name_lower or 'tiểu' in svc_name_lower:
                    tests = LabTest.objects.filter(category__name__icontains='Sinh hóa')
                else:
                    tests = LabTest.objects.all()[:3]
            else:
                tests = LabTest.objects.filter(category__name__icontains=cat)
                
            for test in tests:
                _, detail_created = LabOrderDetail.objects.get_or_create(
                    order=lab_order, 
                    test=test, 
                    defaults={'price_at_time': test.price}
                )
                if detail_created:
                    tests_added_count += 1

        self.stdout.write(self.style.SUCCESS(f"Backfill complete! Created {created_count} new LabOrders and added {tests_added_count} new LabOrderDetails."))
