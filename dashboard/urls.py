from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('gestao/', views.dashboard_gestao_view, name='gestao'),
    path('pedagogico/', views.dashboard_pedagogico_view, name='pedagogico'),
    path('financeiro/', views.dashboard_financeiro_view, name='financeiro'),
]