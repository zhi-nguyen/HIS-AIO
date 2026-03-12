"""
BillingService — Nghiệp vụ viện phí
"""
import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from .models import Invoice, InvoiceLineItem, Payment, InvoiceStatus, ServiceCatalog


class BillingService:
    """Service class xử lý toàn bộ nghiệp vụ tính tiền, hóa đơn và thanh toán."""

    @staticmethod
    def get_or_create_invoice(visit, created_by=None) -> Invoice:
        """
        Lấy hoặc tạo mới hóa đơn cho lượt khám.
        
        Mỗi Visit chỉ có 1 hóa đơn đang active (PENDING/PARTIAL).
        Nếu đã có hóa đơn PAID, tạo hóa đơn mới cho dịch vụ bổ sung.
        """
        # Tìm hóa đơn đang active
        existing = Invoice.objects.filter(
            visit=visit,
            status__in=[InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]
        ).first()
        
        if existing:
            return existing
        
        # Tạo số hóa đơn: INV-YYYYMMDD-XXXXXX
        today_str = timezone.now().strftime('%Y%m%d')
        invoice_number = f"INV-{today_str}-{uuid.uuid4().hex[:6].upper()}"
        
        # Lấy bảng giá mặc định
        from .models import PriceList
        price_list = PriceList.objects.filter(is_default=True, is_active=True).first()
        
        invoice = Invoice.objects.create(
            visit=visit,
            patient=visit.patient,
            invoice_number=invoice_number,
            price_list=price_list,
            created_by=created_by,
        )
        
        return invoice

    @staticmethod
    def add_line_item(
        invoice: Invoice,
        item_name: str,
        quantity: int,
        unit_price,
        service: ServiceCatalog = None,
        related_order_type: str = None,
        related_order_id=None,
        insurance_covered=0,
    ) -> InvoiceLineItem:
        """Thêm một dòng dịch vụ/thuốc vào hóa đơn và tính lại tổng."""
        item = InvoiceLineItem.objects.create(
            invoice=invoice,
            service=service,
            item_name=item_name,
            quantity=quantity,
            unit_price=unit_price,
            total_price=unit_price * quantity,   # also computed in model.save()
            insurance_covered=insurance_covered,
            related_order_type=related_order_type,
            related_order_id=related_order_id,
        )
        
        # Cập nhật lại tổng hóa đơn
        invoice.calculate_totals()
        return item

    @staticmethod
    def process_payment(invoice: Invoice, amount, payment_method: str, cashier) -> Payment:
        """
        Ghi nhận một lần thanh toán.
        
        Tự động cập nhật invoice.paid_amount và invoice.status qua Payment.save().
        
        Raises:
            ValueError: Nếu hóa đơn đã thanh toán đủ hoặc đã hủy.
        """
        if invoice.status == InvoiceStatus.PAID:
            raise ValueError("Hóa đơn đã thanh toán đủ.")
        if invoice.status == InvoiceStatus.CANCELLED:
            raise ValueError("Hóa đơn đã bị hủy.")
        
        today_str = timezone.now().strftime('%Y%m%d')
        receipt_number = f"RCP-{today_str}-{uuid.uuid4().hex[:6].upper()}"
        
        # Determine if the payment will fully pay the invoice
        totals = invoice.payments.aggregate(
            paid=Sum('amount', filter=Q(is_refund=False)),
            refunded=Sum('amount', filter=Q(is_refund=True))
        )
        total_paid_so_far = (totals['paid'] or 0) - (totals['refunded'] or 0)
        will_be_paid = (total_paid_so_far + amount) >= invoice.patient_payable

        payment = Payment.objects.create(
            invoice=invoice,
            receipt_number=receipt_number,
            amount=amount,
            payment_method=payment_method,
            cashier=cashier,
        )
        
        # If invoice is now paid, create LIS and RIS orders.
        if will_be_paid:
            BillingService._process_paid_invoice_orders(invoice)
            
        return payment

    @staticmethod
    def _process_paid_invoice_orders(invoice: Invoice):
        """
        Process items in the invoice that require creation of LIS/RIS orders
        now that the invoice is paid.
        """
        from apps.medical_services.paraclinical.models import ServiceOrder
        from apps.medical_services.lis.models import LabOrder, LabTest, LabOrderDetail
        from apps.medical_services.ris.models import ImagingOrder, ImagingProcedure
        
        visit = invoice.visit
        lis_notified_for_new = False
        lis_notified_for_update = False
        
        cls_items = invoice.items.filter(related_order_type='CLS', related_order_id__isnull=False)
        for item in cls_items:
            try:
                order = ServiceOrder.objects.get(id=item.related_order_id)
                service = order.service
                
                # --- LIS MODULE --- 
                lis_categories = ['Huyết học', 'Sinh hóa', 'Miễn dịch', 'Vi sinh', 'Miễn dịch - Huyết thanh', 'XN', 'LAB']
                if service.category in lis_categories:
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
                            doctor=order.requester,
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
                            
                    # Notify LIS if new tests were added
                    if tests_added and not lis_notified_for_update:
                        lis_notified_for_update = True
                        def send_ws_update():
                            from channels.layers import get_channel_layer
                            from asgiref.sync import async_to_sync
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Billing service pushing lis.order_updated for {lab_order.id}")
                            
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
                
                # --- RIS MODULE ---
                ris_categories = ['CĐHA', 'Thăm dò chức năng', 'CDHA', 'IMAGING']
                if service.category in ris_categories:
                    procedure = ImagingProcedure.objects.filter(name__icontains=service.name).first()
                    if not procedure:
                        procedure = ImagingProcedure.objects.first()

                    if procedure:
                        imaging_order = ImagingOrder.objects.create(
                            visit=visit,
                            patient=visit.patient,
                            doctor=order.requester,
                            procedure=procedure,
                            clinical_indication=f"Chỉ định lâm sàng: {service.name}",
                            status=ImagingOrder.Status.PENDING,
                            priority=ImagingOrder.Priority.URGENT if order.priority == 'STAT' else ImagingOrder.Priority.NORMAL,
                            accession_number=f"ACC-{uuid.uuid4().hex[:8].upper()}"
                        )
                        
                        def send_ris_ws_update():
                            from channels.layers import get_channel_layer
                            from asgiref.sync import async_to_sync
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"Billing service pushing ris.order_updated for {imaging_order.id}")
                            
                            channel_layer = get_channel_layer()
                            if channel_layer is not None:
                                async_to_sync(channel_layer.group_send)(
                                    "ris_updates",
                                    {
                                        "type": "ris.order_updated",
                                        "action": "created",
                                        "order_id": str(imaging_order.id),
                                        "status": imaging_order.status,
                                    }
                                )
                        transaction.on_commit(send_ris_ws_update)
                        
                # Update ServiceOrder status to PAID
                order.status = ServiceOrder.Status.ORDERED
                order.save(update_fields=['status'])
                
            except ServiceOrder.DoesNotExist:
                pass

        # --- PHARMACY MODULE ---
        # Khi hóa đơn thanh toán xong, kiểm tra có đơn thuốc nào liên kết không
        # (items có related_order_type='PRESCRIPTION' được tạo bởi finalize_prescription_to_invoice)
        prescription_items = invoice.items.filter(related_order_type='PRESCRIPTION')
        if prescription_items.exists():
            # Tìm các Prescription thông qua PrescriptionDetail
            from apps.medical_services.pharmacy.models import Prescription, PrescriptionDetail
            prescription_ids = set()
            for item in prescription_items:
                try:
                    detail = PrescriptionDetail.objects.get(id=item.related_order_id)
                    prescription_ids.add(detail.prescription_id)
                except PrescriptionDetail.DoesNotExist:
                    pass

            for rx_id in prescription_ids:
                def send_pharmacist_ws(pid=rx_id):
                    try:
                        prescription = Prescription.objects.select_related(
                            'visit', 'visit__patient'
                        ).prefetch_related(
                            'details', 'details__medication'
                        ).get(id=pid)
                    except Prescription.DoesNotExist:
                        return

                    from channels.layers import get_channel_layer
                    from asgiref.sync import async_to_sync
                    import logging
                    logger = logging.getLogger(__name__)

                    channel_layer = get_channel_layer()
                    if channel_layer is None:
                        logger.error("No channel layer — skipping pharmacist WS notify from billing")
                        return

                    patient = prescription.visit.patient
                    meds = [
                        {
                            'name': d.medication.name,
                            'quantity': d.quantity,
                            'unit': d.medication.unit,
                            'usage_instruction': d.usage_instruction,
                            'duration_days': d.duration_days,
                        }
                        for d in prescription.details.select_related('medication').all()
                    ]
                    async_to_sync(channel_layer.group_send)(
                        "pharmacist_updates",
                        {
                            "type": "pharmacist.prescription_ready",
                            "prescription_id": str(prescription.id),
                            "prescription_code": prescription.prescription_code,
                            "visit_code": prescription.visit.visit_code,
                            "patient_name": patient.full_name if patient else '—',
                            "patient_dob": str(patient.date_of_birth) if patient and patient.date_of_birth else None,
                            "patient_gender": patient.gender if patient else None,
                            "diagnosis": prescription.diagnosis or '',
                            "note": prescription.note or '',
                            "medications": meds,
                            "total_price": str(prescription.total_price),
                            "event_type": "ready",
                            "timestamp": timezone.now().isoformat(),
                        }
                    )
                    logger.info(f"Billing pushed pharmacist.prescription_ready for {prescription.prescription_code}")

                transaction.on_commit(send_pharmacist_ws)


    @staticmethod
    @transaction.atomic
    def finalize_prescription_to_invoice(prescription) -> Invoice:
        """
        Chuyển toàn bộ thuốc trong đơn thành các dòng InvoiceLineItem,
        có tính toán bảo hiểm.
        """
        visit = prescription.visit
        invoice = BillingService.get_or_create_invoice(visit)
        
        benefit_rate = Decimal('0.00')
        if visit.insurance_number and visit.insurance_benefit_rate:
            benefit_rate = Decimal(str(visit.insurance_benefit_rate)) / Decimal('100.00')
        
        for detail in prescription.details.select_related('medication').all():
            already_exists = InvoiceLineItem.objects.filter(
                invoice=invoice,
                related_order_type='PRESCRIPTION',
                related_order_id=detail.id,
            ).exists()
            
            if not already_exists:
                unit_price = detail.unit_price or detail.medication.selling_price
                quantity = detail.quantity
                
                # Tính BHYT chi trả
                total_raw_price = Decimal(str(quantity)) * Decimal(str(unit_price))
                insurance_covered = total_raw_price * benefit_rate
                
                BillingService.add_line_item(
                    invoice=invoice,
                    item_name=f"{detail.medication.name} x {quantity} {detail.medication.unit}",
                    quantity=quantity,
                    unit_price=unit_price,
                    related_order_type='PRESCRIPTION',
                    related_order_id=detail.id,
                    insurance_covered=insurance_covered,
                )
        
        # Broadcast WS to notify billing module
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                "billing_updates",
                {
                    "type": "billing.invoice_updated",
                    "invoice_id": str(invoice.id),
                    "invoice_number": invoice.invoice_number,
                    "visit_code": invoice.visit.visit_code,
                    "patient_name": invoice.patient.full_name,
                }
            )

        return invoice

    @staticmethod
    def get_invoice_summary(visit) -> dict:
        """Lấy tóm tắt viện phí cho một lượt khám."""
        invs = Invoice.objects.filter(visit=visit).prefetch_related('items', 'payments')
        
        result = []
        for inv in invs:
            result.append({
                'invoice_number': inv.invoice_number,
                'status': inv.status,
                'total_amount': float(inv.total_amount),
                'discount_amount': float(inv.discount_amount),
                'insurance_coverage': float(inv.insurance_coverage),
                'patient_payable': float(inv.patient_payable),
                'paid_amount': float(inv.paid_amount),
                'remaining': float(inv.patient_payable - inv.paid_amount),
                'item_count': inv.items.count(),
            })
        
        return result
