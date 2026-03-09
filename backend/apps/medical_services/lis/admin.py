from django.contrib import admin

# Register your models here.

from .models import LabCategory, LabTest, LabOrder, LabOrderDetail, LabSample, LabResult

admin.site.register(LabCategory)
admin.site.register(LabTest)
admin.site.register(LabOrder)
admin.site.register(LabOrderDetail)
admin.site.register(LabSample)
admin.site.register(LabResult)
