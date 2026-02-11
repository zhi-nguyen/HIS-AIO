"""
URL Configuration cho Insurance Mock API.
"""

from django.urls import path
from . import views

app_name = 'insurance_mock'

urlpatterns = [
    path('lookup/', views.lookup_insurance, name='lookup_insurance'),
]
