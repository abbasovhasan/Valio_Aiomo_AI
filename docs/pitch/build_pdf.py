"""Create the pitch PDF from the visually verified Artifact Tool PNG renders.

The PPTX is the editable source. This fallback avoids changing bundled runtime
dependencies when the native PDF exporter cannot resolve a standard font.
"""
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

source, output = map(Path, sys.argv[1:3])
pages = sorted(source.glob('slide-??.png'))
if len(pages) != 7:
    raise SystemExit('Expected exactly seven verified slide renders')
pdf = canvas.Canvas(str(output), pagesize=(960, 540), pageCompression=1)
pdf.setTitle('Aimo Order Desk - local review draft')
pdf.setAuthor('Aimo Order Desk')
pdf.setSubject('Rewind & Repair - Trusted Trade Agents prototype')
for page in pages:
    pdf.drawImage(ImageReader(str(page)), 0, 0, width=960, height=540)
    pdf.showPage()
pdf.save()
print(f'Created {len(pages)}-page PDF')
