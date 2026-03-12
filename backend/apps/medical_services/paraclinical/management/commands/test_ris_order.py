from django.core.management.base import BaseCommand
from apps.medical_services.paraclinical.models import ServiceList
from apps.core_services.reception.models import Visit
from apps.medical_services.paraclinical.services import OrderingService
from apps.medical_services.ris.models import ImagingOrder

class Command(BaseCommand):
    help = 'Test RIS Order Creation'

    def handle(self, *args, **options):
        self.stdout.write("Starting test...")
        visit = Visit.objects.last()
        self.stdout.write(f"Visit: {visit.id if visit else 'None'}")

        imaging_service = ServiceList.objects.filter(category='CĐHA').first()
        self.stdout.write(f"Service: {imaging_service.name if imaging_service else 'None'} ({imaging_service.category if imaging_service else ''})")

        if visit and imaging_service:
            from apps.core_services.authentication.models import Staff
            staff = Staff.objects.first()
            requester_id = str(staff.id) if staff else 'a42d2a41-e970-4f51-b0db-6e60b24dc6cd'
            
            self.stdout.write(f"Calling OrderingService.create_lab_order for service {imaging_service.id}...")
            try:
                orders = OrderingService.create_lab_order(str(visit.id), [str(imaging_service.id)], requester_id)
                self.stdout.write(f"Created {len(orders)} ServiceOrders.")
                
                ris_count = ImagingOrder.objects.filter(visit=visit).count()
                self.stdout.write(f"Found {ris_count} ImagingOrders for visit {visit.id}")

                latest_ris = ImagingOrder.objects.filter(visit=visit).last()
                if latest_ris:
                    self.stdout.write(f"Latest RIS order: {latest_ris.id} - {latest_ris.procedure.name}")
                else:
                    self.stdout.write("No RIS orders found!")

            except Exception as e:
                self.stdout.write(f"Error: {e}")
