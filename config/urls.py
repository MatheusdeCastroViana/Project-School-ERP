from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='accounts/login/', permanent=False)), 
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('usuarios/', include('usuarios.urls')),
]