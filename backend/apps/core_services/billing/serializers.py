from rest_framework import serializers
from .models import ServiceCatalog, PriceList, ServicePrice

class ServicePriceSerializer(serializers.ModelSerializer):
    price_list_name = serializers.CharField(source='price_list.name', read_only=True)
    
    class Meta:
        model = ServicePrice
        fields = '__all__'

class ServiceCatalogSerializer(serializers.ModelSerializer):
    prices = ServicePriceSerializer(many=True, read_only=True)
    
    class Meta:
        model = ServiceCatalog
        fields = '__all__'
