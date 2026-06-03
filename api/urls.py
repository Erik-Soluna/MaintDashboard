from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('', views.ApiRoot.as_view(), name='root'),
    path('diagnostics/health/', views.DiagnosticsHealth.as_view(), name='diag_health'),
    path('diagnostics/summary/', views.DiagnosticsSummary.as_view(), name='diag_summary'),
    path('data/<str:app_label>/<str:model_name>/', views.ModelListView.as_view(), name='model_list'),
    path('data/<str:app_label>/<str:model_name>/<int:pk>/', views.ModelDetailView.as_view(), name='model_detail'),
]
