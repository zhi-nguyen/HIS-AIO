from typing import List
from django.db import transaction
from .models import ServiceOrder, ServiceList, ServiceResult
from apps.core_services.reception.models import Visit
from apps.core_services.billing.services import BillingService

class OrderingService:
    @staticmethod
    def create_lab_order(visit_id: str, service_ids: List[str], requester_id: str) -> List[ServiceOrder]:
        """
        Create ServiceOrder records for a list of service IDs.
        """
        created_orders = []
        visit = Visit.objects.get(id=visit_id)
        
        with transaction.atomic():
            # Get or create invoice for this visit
            invoice = BillingService.get_or_create_invoice(visit)
            
            # Tracking flags to avoid sending duplicate WS messages in one batch
            lis_notified_for_new = False
            lis_notified_for_update = False
            
            for service_id in service_ids:
                service = ServiceList.objects.get(id=service_id)
                # Determine priority based on visit priority (simplified)
                priority = 'STAT' if visit.priority == Visit.Priority.EMERGENCY else 'ROUTINE'
                
                order = ServiceOrder.objects.create(
                    visit=visit,
                    service=service,
                    requester_id=requester_id,
                    status=ServiceOrder.Status.UNPAID,  # Hold order until paid
                    priority=priority
                )
                
                # Initialize empty result placeholder
                ServiceResult.objects.create(order=order)
                
                # Add to Billing Invoice
                BillingService.add_line_item(
                    invoice=invoice,
                    item_name=service.name,
                    quantity=1,
                    unit_price=service.price,
                    service=None,  # Not linked to ServiceCatalog, just plain line item
                    related_order_type='CLS',
                    related_order_id=order.id
                )
                created_orders.append(order)
                
                # --- SYNCHRONIZE WITH LIS MODULE --- 
                # If the service is a Lab Test, create a corresponding LabOrder in the LIS module for the technicians.
                # (In this prototype, we map by category. In production, there would be a mapping table.)
                lis_categories = ['Huyết học', 'Sinh hóa', 'Miễn dịch', 'Vi sinh', 'Miễn dịch - Huyết thanh', 'XN', 'LAB']
                if service.category in lis_categories:
                    from apps.medical_services.lis.models import LabOrder, LabTest, LabOrderDetail
                    from apps.core_services.authentication.models import Staff
                    
                    doctor = Staff.objects.filter(id=requester_id).first() if requester_id else None
                    
                    # Find an active LabOrder for this visit, or create a new one
                    lab_order = LabOrder.objects.filter(
                        visit=visit
                    ).exclude(
                        status__in=[LabOrder.Status.COMPLETED, LabOrder.Status.VERIFIED, LabOrder.Status.CANCELLED]
                    ).order_by('-created_at').first()
                    
                    is_new_lab_order = False
                    if not lab_order:
                        lab_order = LabOrder.objects.create(
                            visit=visit,
                            patient=visit.patient,
                            doctor=doctor,
                            status=LabOrder.Status.PENDING,
                        )
                        is_new_lab_order = True
                    
                    # Map the requested service category to LIS LabTests
                    if service.category in ['XN', 'LAB']:
                        svc_name_lower = service.name.lower()
                        if 'máu' in svc_name_lower or 'cbc' in svc_name_lower or 'huyết' in svc_name_lower:
                            tests = LabTest.objects.filter(category__name__icontains='Huyết học')
                        elif 'sinh hóa' in svc_name_lower or 'đường' in svc_name_lower or 'hba1c' in svc_name_lower or 'tiểu' in svc_name_lower:
                            tests = LabTest.objects.filter(category__name__icontains='Sinh hóa')
                        else:
                            tests = LabTest.objects.all()[:3]
                    else:
                        tests = LabTest.objects.filter(category__name__icontains=service.category)
                        
                    tests_added = False
                    for test in tests:
                        LabOrderDetail.objects.create(
                            order=lab_order,
                            test=test,
                            price_at_time=test.price,
                            service_name=service.name
                        )
                        tests_added = True
                            
                    # If this is an existing LabOrder but we added new tests, we must notify LIS
                    # Ensure we notify LIS that new tests are added to the worklist
                    if tests_added and not lis_notified_for_update:
                        lis_notified_for_update = True
                        def send_ws_update():
                            from channels.layers import get_channel_layer
                            from asgiref.sync import async_to_sync
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Paraclinical service pushing lis.order_updated for {lab_order.id}")
                            
                            channel_layer = get_channel_layer()
                            if channel_layer is not None:
                                async_to_sync(channel_layer.group_send)(
                                    "lis_updates",
                                    {
                                        "type": "lis.order_updated",
                                        "action": "created" if is_new_lab_order else "updated", 
                                        "order_id": str(lab_order.id),
                                        "status": lab_order.status,
                                    }
                                )
                        transaction.on_commit(send_ws_update)
                # -----------------------------------

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
            status__in=[ServiceOrder.Status.UNPAID, ServiceOrder.Status.ORDERED, ServiceOrder.Status.PROCESSING, ServiceOrder.Status.COMPLETED]
        ).select_related('service')
        
        for order in existing_orders:
            duplicates.append(order.service.name)
            
        return duplicates
