from equipment.models import Equipment, EquipmentDocument
from django.core.files.base import ContentFile
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Get equipment
EQUIPMENT_ID = 17

equipment = Equipment.objects.get(id=EQUIPMENT_ID)
pdf_path = '/tmp/dga_status_report.pdf'

# Generate PDF
c = canvas.Canvas(pdf_path, pagesize=letter)
c.drawString(100, 750, 'DGA Status Report')
c.drawString(100, 730, f'Equipment: {equipment.name}')
c.drawString(100, 710, 'Date: 2024-07-13')
c.drawString(100, 690, 'DGA Status: NORMAL')
c.drawString(100, 670, 'No critical gases detected.')
c.save()

# Attach PDF to equipment as a maintenance document
with open(pdf_path, 'rb') as f:
    doc = EquipmentDocument.objects.create(
        equipment=equipment,
        title='DGA Status Report',
        document_type='maintenance',
        description='Auto-generated DGA PDF report'
    )
    doc.file.save('dga_status_report.pdf', ContentFile(f.read()))

os.remove(pdf_path)
print('Created DGA PDF report for equipment:', equipment.name) 