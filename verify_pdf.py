import sys
sys.stdout.reconfigure(encoding='utf-8')
import pythoncom
import win32com.client
SRC = r'C:\Users\camer\Documents\Code\webscrape\SEA_2027_Budget_Comparison.xlsx'
PDF = r'C:\Users\camer\Documents\Code\webscrape\SEA_2027_Budget_Comparison.pdf'
pythoncom.CoInitialize()
excel = win32com.client.DispatchEx('Excel.Application')
excel.Visible = False
excel.DisplayAlerts = False
wb = excel.Workbooks.Open(SRC, UpdateLinks=0, ReadOnly=True)
excel.CalculateFullRebuild()
wb.ExportAsFixedFormat(0, PDF)  # xlTypePDF = 0
wb.Close(SaveChanges=False)
excel.Quit()
pythoncom.CoUninitialize()
print('saved', PDF)
