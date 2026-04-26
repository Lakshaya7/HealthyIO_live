from django.contrib import admin
from .models import HealthLog, UserProfile

admin.site.register(HealthLog)
admin.site.register(UserProfile)