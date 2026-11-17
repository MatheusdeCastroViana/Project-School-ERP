from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView

admin.site.site_header = 'Painel de administração'
admin.site.site_title = 'Painel de administração'
admin.site.index_title = 'Painel de administração'

urlpatterns = [
    path('', RedirectView.as_view(url='accounts/login/', permanent=False)), 
    path('admin/login/', RedirectView.as_view(url='/accounts/login/?next=/admin/', permanent=False)),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('dashboard/', include('dashboard.urls')),
]