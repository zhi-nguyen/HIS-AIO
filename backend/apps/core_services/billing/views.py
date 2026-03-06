import logging

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import Invoice, InvoiceLineItem, ServiceCatalog, Payment, InvoiceStatus
from .serializers import (
    InvoiceSerializer,
    InvoiceLineItemSerializer,
    PaymentSerializer,
    ServiceCatalogSerializer,
)
from .services import BillingService

logger = logging.getLogger(__name__)


class ServiceCatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only viewset for Service Catalog (Staff search services)
    """
    queryset = ServiceCatalog.objects.filter(is_active=True).order_by('name')
    serializer_class = ServiceCatalogSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['code', 'name']
    filterset_fields = ['service_type']


class InvoiceViewSet(viewsets.ModelViewSet):
    """
    Hóa đơn viện phí — quản lý toàn bộ chu trình tính tiền.
    
    GET    /billing/invoices/?visit={visit_id}      — Lấy danh sách hóa đơn
    POST   /billing/invoices/                        — Tạo hóa đơn (tự động từ visit)
    GET    /billing/invoices/{id}/                   — Chi tiết hóa đơn
    POST   /billing/invoices/{id}/add-item/          — Thêm dòng dịch vụ
    POST   /billing/invoices/{id}/pay/               — Thanh toán
    POST   /billing/invoices/{id}/finalize-prescription/ — Chuyển đơn thuốc thành dòng HD
    """
    serializer_class = InvoiceSerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['invoice_number', 'patient__patient_code']
    filterset_fields = ['status', 'visit', 'patient']

    def get_queryset(self):
        return Invoice.objects.select_related(
            'visit', 'patient', 'price_list', 'created_by'
        ).prefetch_related(
            'items', 'items__service',
            'payments', 'payments__cashier'
        ).order_by('-created_time')

    def create(self, request, *args, **kwargs):
        """
        Tạo hoặc lấy hóa đơn cho Visit.
        
        Body: { "visit": "<visit_uuid>" }
        """
        visit_id = request.data.get('visit')
        if not visit_id:
            return Response({'error': 'visit là bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.core_services.reception.models import Visit
        try:
            visit = Visit.objects.get(id=visit_id)
        except Visit.DoesNotExist:
            return Response({'error': 'Lượt khám không tồn tại'}, status=status.HTTP_404_NOT_FOUND)
        
        # Lấy staff hiện tại (nếu có)
        created_by = getattr(request.user, 'staff_profile', None)
        
        invoice = BillingService.get_or_create_invoice(visit, created_by=created_by)
        serializer = self.get_serializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='add-item')
    def add_item(self, request, pk=None):
        """
        Thêm một dòng dịch vụ/thuốc vào hóa đơn.
        
        Body: {
            "item_name": "Khám bệnh tổng quát",
            "quantity": 1,
            "unit_price": "150000.00",
            "service_id": "<uuid>",          // optional
            "related_order_type": "LAB_ORDER", // optional
            "related_order_id": "<uuid>",    // optional
            "insurance_covered": "0.00"     // optional
        }
        """
        invoice = self.get_object()
        
        if invoice.status in [InvoiceStatus.PAID, InvoiceStatus.CANCELLED]:
            return Response(
                {'error': 'Không thể thêm dịch vụ vào hóa đơn đã thanh toán hoặc đã hủy'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        item_name = request.data.get('item_name')
        quantity = request.data.get('quantity', 1)
        unit_price = request.data.get('unit_price')
        
        if not item_name or not unit_price:
            return Response(
                {'error': 'item_name và unit_price là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service = None
        service_id = request.data.get('service_id')
        if service_id:
            service = ServiceCatalog.objects.filter(id=service_id).first()
        
        item = BillingService.add_line_item(
            invoice=invoice,
            item_name=item_name,
            quantity=int(quantity),
            unit_price=unit_price,
            service=service,
            related_order_type=request.data.get('related_order_type'),
            related_order_id=request.data.get('related_order_id'),
            insurance_covered=request.data.get('insurance_covered', 0),
        )
        
        invoice.refresh_from_db()
        serializer = self.get_serializer(invoice)
        logger.info(f"Added item '{item_name}' to invoice {invoice.invoice_number}")
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        """
        Ghi nhận thanh toán cho hóa đơn.
        
        Body: {
            "amount": "500000.00",
            "payment_method": "CASH" | "CARD" | "TRANSFER" | "MOMO" | "VNPAY" | "INSURANCE"
        }
        """
        invoice = self.get_object()
        
        amount = request.data.get('amount')
        payment_method = request.data.get('payment_method', 'CASH')
        
        if not amount:
            return Response({'error': 'amount là bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate payment method
        from .models import PaymentMethod
        valid_methods = [m.value for m in PaymentMethod]
        if payment_method not in valid_methods:
            return Response(
                {'error': f'Phương thức thanh toán không hợp lệ. Hợp lệ: {valid_methods}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cashier = getattr(request.user, 'staff_profile', None)
        if not cashier:
            return Response(
                {'error': 'Cần đăng nhập với tài khoản nhân viên để thanh toán'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            payment = BillingService.process_payment(
                invoice=invoice,
                amount=amount,
                payment_method=payment_method,
                cashier=cashier,
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        invoice.refresh_from_db()
        serializer = self.get_serializer(invoice)
        logger.info(
            f"Payment {payment.receipt_number}: {amount} VND via {payment_method} "
            f"for invoice {invoice.invoice_number}"
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='finalize-prescription')
    def finalize_prescription(self, request, pk=None):
        """
        Chuyển đơn thuốc thành dòng hóa đơn.
        
        Body: { "prescription_id": "<uuid>" }
        """
        invoice = self.get_object()
        prescription_id = request.data.get('prescription_id')
        
        if not prescription_id:
            return Response(
                {'error': 'prescription_id là bắt buộc'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.medical_services.pharmacy.models import Prescription
        try:
            prescription = Prescription.objects.get(
                id=prescription_id,
                visit=invoice.visit
            )
        except Prescription.DoesNotExist:
            return Response(
                {'error': 'Đơn thuốc không tồn tại hoặc không thuộc lượt khám này'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        BillingService.finalize_prescription_to_invoice(prescription)
        invoice.refresh_from_db()
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='by-visit')
    def by_visit(self, request):
        """
        Lấy toàn bộ hóa đơn và tóm tắt viện phí cho một lượt khám.
        
        GET /billing/invoices/by-visit/?visit_id={uuid}
        """
        visit_id = request.query_params.get('visit_id')
        if not visit_id:
            return Response({'error': 'visit_id là bắt buộc'}, status=status.HTTP_400_BAD_REQUEST)
        
        from apps.core_services.reception.models import Visit
        try:
            visit = Visit.objects.get(id=visit_id)
        except Visit.DoesNotExist:
            return Response({'error': 'Lượt khám không tồn tại'}, status=status.HTTP_404_NOT_FOUND)
        
        invoices = self.get_queryset().filter(visit=visit)
        serializer = self.get_serializer(invoices, many=True)
        summary = BillingService.get_invoice_summary(visit)
        
        return Response({
            'invoices': serializer.data,
            'summary': summary,
        })