from rest_framework import serializers
from .models import Invoice, InvoiceLineItem, Payment, ServiceCatalog


class ServiceCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCatalog
        fields = ['id', 'code', 'name', 'service_type', 'base_price', 'bhyt_code', 'bhyt_price', 'is_active']


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = [
            'id', 'invoice', 'service', 'item_name', 'quantity',
            'unit_price', 'total_price', 'insurance_covered',
            'is_paid', 'related_order_type', 'related_order_id', 'created_time'
        ]
        read_only_fields = ['total_price', 'created_time']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'receipt_number', 'amount',
            'payment_method', 'payment_time', 'cashier',
            'is_refund', 'refund_reason', 'note'
        ]
        read_only_fields = ['receipt_number', 'payment_time']

class VisitInsuranceSerializer(serializers.Serializer):
    """
    Trả về thông tin BHYT đã snapshot vào Visit lúc đăng ký.
    Dùng cho InvoiceSerializer để billing không cần gọi lại cổng BH.
    """
    id                    = serializers.UUIDField(read_only=True)
    visit_code            = serializers.CharField(read_only=True)
    insurance_number      = serializers.CharField(read_only=True, allow_null=True)
    insurance_benefit_rate = serializers.IntegerField(read_only=True, allow_null=True)
    insurance_card_expire = serializers.DateField(read_only=True, allow_null=True)


class InvoiceSerializer(serializers.ModelSerializer):
    items        = InvoiceLineItemSerializer(many=True, read_only=True)
    payments     = PaymentSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    # nested visit với insurance snapshot
    visit_detail = VisitInsuranceSerializer(source='visit', read_only=True)

    class Meta:
        model = Invoice
        fields = [
            'id', 'visit', 'visit_detail', 'patient', 'invoice_number', 'price_list',
            'total_amount', 'discount_amount', 'insurance_coverage',
            'patient_payable', 'paid_amount', 'status', 'status_display',
            'created_time', 'updated_time', 'created_by', 'note',
            'items', 'payments',
        ]
        read_only_fields = [
            'invoice_number', 'total_amount', 'patient_payable',
            'paid_amount', 'created_time', 'updated_time',
        ]


