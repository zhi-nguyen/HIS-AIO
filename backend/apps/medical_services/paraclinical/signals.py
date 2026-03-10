from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from apps.core_services.billing.models import Invoice, InvoiceStatus, InvoiceLineItem
from .models import ServiceOrder

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Invoice)
def release_cls_orders_on_payment(sender, instance, **kwargs):
    """
    Khi Invoice được thanh toán (PAID hoặc PARTIAL),
    tìm các chỉ định CLS tương ứng (từ InvoiceLineItem)
    và thả chúng từ trạng thái UNPAID sang ORDERED.
    """
    if instance.status in [InvoiceStatus.PAID, InvoiceStatus.PARTIAL]:
        try:
            # Lấy tất cả line items liên quan đến hoá đơn này và xuất phát từ CLS
            cls_items = InvoiceLineItem.objects.filter(
                invoice=instance,
                related_order_type='CLS'
            )
            
            order_ids = [item.related_order_id for item in cls_items if item.related_order_id]
            
            if order_ids:
                # Cập nhật các phiếu chỉ định CLS từ UNPAID sang ORDERED
                updated_count = ServiceOrder.objects.filter(
                    id__in=order_ids,
                    status=ServiceOrder.Status.UNPAID
                ).update(status=ServiceOrder.Status.ORDERED)
                
                # Optional: Update is_paid for the line items
                if instance.status == InvoiceStatus.PAID:
                    cls_items.update(is_paid=True)
                    
                logger.info(f"Released {updated_count} CLS orders for Invoice {instance.invoice_number}")
                
        except Exception as e:
            logger.error(f"Error releasing CLS orders for Invoice {instance.invoice_number}: {e}", exc_info=True)
