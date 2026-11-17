import sys
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf
doc = pymupdf.open('SEA_2027_Budget_Comparison.pdf')
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=110)
    pix.save(f'pg_{i+1:02d}.png')
print('done')
