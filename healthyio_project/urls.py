from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Links to allauth for Google Login
    path('accounts/', include('allauth.urls')), 
    # Links to our core app (This replaces the Django Rocket page!)
    path('', include('core.urls')),
]
