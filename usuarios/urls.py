from django.urls import path
from . import views_2fa

app_name = 'usuarios'

urlpatterns = [
    path('dashboard/', views_2fa.dashboard, name='dashboard'),
    path('logout/', views_2fa.logout_usuario, name='logout'), # Rota segura com auditoria
    
    path('ativar-2fa/', views_2fa.ativar_2fa, name='ativar_2fa'),
    path('desativar-2fa/', views_2fa.desativar_2fa, name='desativar_2fa'),
    path('verify-2fa/', views_2fa.verificar_2fa, name='verificar_2fa'),
]