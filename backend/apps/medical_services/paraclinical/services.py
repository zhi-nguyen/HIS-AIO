from typing import List
from django.db import transaction
from .models import ServiceOrder, ServiceList, ServiceResult
from apps.core_services.reception.models import Visit

class OrderingService:
    @staticmethod
    def create_lab_order(visit_id: str, service_ids: List[str], requester_id: str) -> List[ServiceOrder]:
        """
        Create ServiceOrder records for a list of service IDs.
        """
        created_orders = []
        visit = Visit.objects.get(id=visit_id)
        
        with transaction.atomic():
            for service_id in service_ids:
                service = ServiceList.objects.get(id=service_id)
                # Determine priority based on visit priority (simplified)
                priority = 'STAT' if visit.priority == Visit.Priority.EMERGENCY else 'ROUTINE'
                
                order = ServiceOrder.objects.create(
                    visit=visit,
                    service=service,
                    requester_id=requester_id,
                    status=ServiceOrder.Status.ORDERED,
                    priority=priority
                )
                
                # Initialize empty result placeholder
                ServiceResult.objects.create(order=order)
                
                created_orders.append(order)
                
            # Update visit status if not already consistent
            if visit.status != Visit.Status.PENDING_RESULTS:
                visit.status = Visit.Status.PENDING_RESULTS
                visit.save(update_fields=['status'])

        return created_orders

    @staticmethod
    def check_duplicate_orders(visit_id: str, service_ids: List[str]) -> List[str]:
        """
        Check if any of the requested services have already been ordered for this visit.
        Returns a list of Service names that are duplicates.
        """
        duplicates = []
        existing_orders = ServiceOrder.objects.filter(
            visit__id=visit_id,
            service__id__in=service_ids,
            status__in=[ServiceOrder.Status.ORDERED, ServiceOrder.Status.PROCESSING, ServiceOrder.Status.COMPLETED]
        ).select_related('service')
        
        for order in existing_orders:
            duplicates.append(order.service.name)
            
        return duplicates
