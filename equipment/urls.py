"""
URL configuration for equipment app.
"""

from django.urls import path
from . import views

app_name = 'equipment'

urlpatterns = [
    # Equipment list and management
    path('', views.equipment_list, name='equipment_list'),
    path('manage/', views.manage_equipment, name='manage_equipment'),
    path('add/', views.add_equipment, name='add_equipment'),
    path('<int:equipment_id>/', views.equipment_detail, name='equipment_detail'),
    path('<int:equipment_id>/edit/', views.edit_equipment, name='edit_equipment'),
    path('<int:equipment_id>/delete/', views.delete_equipment, name='delete_equipment'),
    
    # AJAX endpoints
    path('api/data/', views.get_equipment_data, name='get_equipment_data'),
    path('api/search/', views.search_equipment, name='search_equipment'),
    
    # Components
    path('<int:equipment_id>/components/', views.equipment_components, name='equipment_components'),
    path('<int:equipment_id>/components/add/', views.add_component, name='add_component'),
    
    # Documents
    path('<int:equipment_id>/documents/', views.equipment_documents, name='equipment_documents'),
    path('<int:equipment_id>/documents/add/', views.add_document, name='add_document'),
    path('<int:equipment_id>/scan-reports/', views.scan_reports, name='scan_reports'),
    path('<int:equipment_id>/analyze-reports/', views.analyze_reports, name='analyze_reports'),
    
    # CSV Import/Export
    path('import/csv/', views.import_equipment_csv, name='import_equipment_csv'),
    path('export/csv/', views.export_equipment_csv, name='export_equipment_csv'),
    path('locations/import/csv/', views.import_locations_csv, name='import_locations_csv'),
    path('locations/export/csv/', views.export_locations_csv, name='export_locations_csv'),
]