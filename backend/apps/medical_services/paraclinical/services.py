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
                
                
                # We do not create LIS/RIS orders here anymore. They are on hold until payment.
                # Just notify Billing via WebSocket that new orders need payment.
                def send_billing_ws_update():
                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Paraclinical service pushing billing.invoice_updated for Invoice {invoice.id}")
                    
                    channel_layer = get_channel_layer()
                    if channel_layer is not None:
                        async_to_sync(channel_layer.group_send)(
                            "billing_updates",
                            {
                                "type": "billing.invoice_updated",
                                "action": "updated", 
                                "invoice_id": str(invoice.id),
                            }
                        )
                transaction.on_commit(send_billing_ws_update)
                
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
