"""Open the workbook in real Excel, force full rebuild, scan for errors, dump key values."""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import pythoncom
import win32com.client

SRC = r'C:\Users\camer\Documents\Code\webscrape\SEA_2027_Budget_Comparison.xlsx'
pythoncom.CoInitialize()
excel = win32com.client.DispatchEx('Excel.Application')
excel.Visible = False
excel.DisplayAlerts = False
excel.EnableEvents = False
wb = excel.Workbooks.Open(SRC, UpdateLinks=0, ReadOnly=True)
excel.CalculateFullRebuild()

print('rebuilt — scanning for error values…')
err_cells = []
for ws in wb.Worksheets:
    for row in ws.UsedRange.Rows:
        for cell in row.Cells:
            v = cell.Value
            if isinstance(v, str) and v.startswith('#'):
                err_cells.append((ws.Name, cell.Address, v))
print('error cells:', len(err_cells))
for w, a, v in err_cells[:25]:
    print(' ', w, a, v)

def show(sheet, addr):
    ws = wb.Worksheets(sheet)
    c = ws.Range(addr)
    print(f'{sheet}!{addr:4s} = {c.Value}')

print('\n--- 02 Payslip ---')
for a in ['C13','D13','E13','F13','C14']:
    show('02 Payslip History', a)
print('--- 03 Earnings ---')
for a in ['F8','E16','I16','E22','F22','G10','F33']:
    show('03 UK Earnings Model', a)
print('--- 04 Funds Available ---')
ws = wb.Worksheets('04 Funds Available')
for r in range(6, 27):
    lab, b, c = ws.Range(f'A{r}').Value, ws.Range(f'B{r}').Value, ws.Range(f'C{r}').Value
    if lab:
        print(f'r{r:2d}  {str(lab)[:62]:62s}  {b}  |  {c}')
print('--- 05 tie-outs ---')
for a in ['D20','D34','D36','D57','D69','D101','D136','D148','D149','D150','D151','D152','D153']:
    show('05 Confirmed Cost Base', a)
print('--- S-tab grand totals (B section, SCENARIO TOTAL row) ---')
for s in ['S1','S2','S3','S4','S5','S6','S7','S8','S9']:
    ws = wb.Worksheets(s)
    for r in range(1, ws.UsedRange.Rows.Count + 1):
        if ws.Range(f'A{r}').Value == 'SCENARIO TOTAL':
            print(s, 'TOTAL =', ws.Range(f'D{r}').Value)
            break
print('--- 07 ENVELOPES + TABLE ---')
ws = wb.Worksheets('07 SCENARIO SUMMARY')
for r in range(5, 38):
    vals = [ws.Range(f'{c}{r}').Value for c in 'ABCDEFGHIJKLMNOPQ']
    if vals[0] or vals[11]:
        print(r, vals)
wb.Close(SaveChanges=False)
excel.Quit()
pythoncom.CoUninitialize()
print('\ndone')
