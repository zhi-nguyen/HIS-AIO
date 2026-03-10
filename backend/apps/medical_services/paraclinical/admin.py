
from django.contrib import admin

from .models import ServiceList, ServiceOrder, ServiceResult

admin.site.register(ServiceList)
admin.site.register(ServiceOrder)
admin.site.register(ServiceResult)
