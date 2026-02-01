from django.contrib import admin
from .models import (
    PriceList, ServiceCatalog, ServicePrice, 
    Invoice, InvoiceLineItem, Payment, DepositPayment
)


@admin.register(PriceList)
class PriceListAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_default', 'is_active']
    list_filter = ['is_active', 'is_default']


@admin.register(ServiceCatalog)
class ServiceCatalogAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'service_type', 'base_price', 'is_active']
    list_filter = ['service_type', 'is_active']
    search_fields = ['code', 'name']


@admin.register(ServicePrice)
class ServicePriceAdmin(admin.ModelAdmin):
    list_display = ['service', 'price_list', 'price']
    list_filter = ['price_list']


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'patient', 'total_amount', 'patient_payable', 'paid_amount', 'status']
    list_filter = ['status']
    search_fields = ['invoice_number', 'patient__fullname']
    inlines = [InvoiceLineItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'invoice', 'amount', 'payment_method', 'payment_time']
    list_filter = ['payment_method', 'is_refund']
    search_fields = ['receipt_number']


@admin.register(DepositPayment)
class DepositPaymentAdmin(admin.ModelAdmin):
    list_display = ['receipt_number', 'patient', 'amount', 'used_amount', 'deposit_time']
    search_fields = ['receipt_number', 'patient__fullname']
