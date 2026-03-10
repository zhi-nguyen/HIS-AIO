from django.contrib import admin

# Register your models here.

from .models import AgentProfile, VectorStore, AgentLog

admin.site.register(AgentProfile)
admin.site.register(VectorStore)
admin.site.register(AgentLog)
