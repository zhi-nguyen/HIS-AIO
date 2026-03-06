"""
BillingService — Nghiệp vụ viện phí
"""
import uuid
from django.db import transaction
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
        
        payment = Payment.objects.create(
            invoice=invoice,
            receipt_number=receipt_number,
            amount=amount,
            payment_method=payment_method,
            cashier=cashier,
        )
        
        return payment

    @staticmethod
    @transaction.atomic
    def finalize_prescription_to_invoice(prescription) -> Invoice:
        """
        Chuyển toàn bộ thuốc trong đơn thành các dòng InvoiceLineItem.
        
        Gọi sau khi bác sĩ hoàn tất kê đơn, trước khi BN lên viện phí.
        
        Returns:
            Invoice đã được cập nhật với các dòng thuốc.
        """
        visit = prescription.visit
        invoice = BillingService.get_or_create_invoice(visit)
        
        for detail in prescription.details.select_related('medication').all():
            # Kiểm tra đã có dòng này chưa (tránh duplicate)
            already_exists = InvoiceLineItem.objects.filter(
                invoice=invoice,
                related_order_type='PRESCRIPTION',
                related_order_id=detail.id,
            ).exists()
            
            if not already_exists:
                BillingService.add_line_item(
                    invoice=invoice,
                    item_name=f"{detail.medication.name} x {detail.quantity} {detail.medication.unit}",
                    quantity=detail.quantity,
                    unit_price=detail.unit_price or detail.medication.selling_price,
                    related_order_type='PRESCRIPTION',
                    related_order_id=detail.id,
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
