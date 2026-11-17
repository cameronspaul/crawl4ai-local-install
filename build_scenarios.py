#!/usr/bin/env python3
"""Build SEA_2027_Budget_Comparison.xlsx — budget & itinerary comparison for Cameron's
post-Vietnam/Thailand options, with Australia as the non-negotiable end leg."""
import csv
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.chart import BarChart, Reference
import datetime as dt

OUT = 'SEA_2027_Budget_Comparison.xlsx'

NAVY, ORANGE, STEEL = '16324F', 'E8722A', '2E4A6B'
CREAM, YELLOW = 'FBF7EF', 'FFF3C4'
GREY_LN, LGREENF, LRED, LAMBER, LBLUE = 'D8D2C4', 'D8EFDD', 'FAE3E3', 'FDEBD0', 'E8EEF7'

thin = Side(style='thin', color=GREY_LN)
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)

def sheet(wb, name, tab=NAVY):
    ws = wb.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = tab
    return ws

def C(ws, r, c, v, bold=False, size=9.5, color='26221C', fill=None, border=BOX,
      fmt=None, align=None, wrap=False, italic=False):
    cell = ws.cell(row=r, column=c, value=v)
    cell.font = Font(name='Calibri', bold=bold, size=size, color=color, italic=italic)
    if fill: cell.fill = PatternFill('solid', fgColor=fill)
    if border: cell.border = border
    if fmt: cell.number_format = fmt
    cell.alignment = Alignment(horizontal=align, vertical='center', wrap_text=wrap)
    return cell

def title(ws, r, c1, c2, text, sub=None):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    C(ws, r, c1, text, bold=True, size=16, color='FFFFFF', fill=NAVY, border=None, align='left')
    ws.row_dimensions[r].height = 30
    if sub:
        ws.merge_cells(start_row=r+1, start_column=c1, end_row=r+1, end_column=c2)
        C(ws, r+1, c1, sub, size=8.5, italic=True, color='6B6255', fill=CREAM, border=None, align='left', wrap=True)
        ws.row_dimensions[r+1].height = 22

def band(ws, r, c1, c2, text):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    C(ws, r, c1, text, bold=True, size=10, color='FFFFFF', fill=ORANGE, border=None, align='left')
    ws.row_dimensions[r].height = 18

def hdr(ws, r, col_vals, height=22):
    for c, v in col_vals:
        C(ws, r, c, v, bold=True, size=8.5, color='FFFFFF', fill=STEEL, align='center', wrap=True)
    ws.row_dimensions[r].height = height

def footer(ws, r, c2):
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=c2)
    C(ws, r, 1, 'SEA 2027 · Budget vs Australia · built 16 Nov 2026 · GBP per person · prices checked Nov 2026 · not financial advice',
      size=7, italic=True, color='9A9184', border=None, align='left')

def widths(ws, wd):
    for col, w in wd.items():
        ws.column_dimensions[col].width = w

def note(ws, r, c1, c2, text, fill=CREAM, color='4A4238', size=8.5, height=26):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    C(ws, r, c1, text, size=size, color=color, fill=fill, border=None, align='left', wrap=True)
    ws.row_dimensions[r].height = height

def inp(ws, r, c, v, fmt='£#,##0.00'):
    C(ws, r, c, v, bold=True, color='7A4A00', fill=YELLOW, fmt=fmt, align='center')

def money(ws, r, c, f, bold=False, fill=None, fmt='£#,##0.00'):
    C(ws, r, c, f, bold=bold, fill=fill, fmt=fmt, align='center')

def lab(ws, r, c, v, bold=False, size=9.5, wrap=False, color='26221C'):
    C(ws, r, c, v, bold=bold, size=size, border=None, align='left', wrap=wrap, color=color)

def merge_lab(ws, r, c1, c2, v, bold=False, size=9.5, color='26221C', wrap=False):
    ws.merge_cells(start_row=r, start_column=c1, end_row=r, end_column=c2)
    C(ws, r, c1, v, bold=bold, size=size, border=None, align='left', wrap=wrap, color=color)

GBP = '£#,##0.00'; GBP0 = '£#,##0'; PCT = '0.0%'; INT = '0'; DGBP = '£0.00 "/day"'

wb = Workbook()
wb.remove(wb['Sheet'])

# ================= data =================
with open('SEA_2027_STOPS.csv', encoding='utf-8') as f:
    STOPS = list(csv.DictReader(f))
with open('SEA_2027_LEGS.csv', encoding='utf-8') as f:
    LEGS = list(csv.DictReader(f))

def legs_by_no(*nos):
    out = []
    for no in nos:
        l = next(l for l in LEGS if int(l['leg_no']) == no)
        out.append((f"{l['from_name']} → {l['to_name']}", l['date'], float(l['gbp'])))
    return out

def stop(name):
    r = next(r for r in STOPS if r['location'] == name)
    d1, d2 = dt.date.fromisoformat(r['start_date']), dt.date.fromisoformat(r['end_date'])
    lbl = f"{d1.day} {d1.strftime('%b')}–{d2.day} {d2.strftime('%b')}"
    return (r['location'], lbl, int(r['nights']), float(r['all_in_gbp']))

def stops_sum(names):
    rows = [stop(n) for n in names]
    return sum(x[3] for x in rows), sum(x[2] for x in rows)

VNTH_NAMES = [r['location'] for r in STOPS if r['country'] in ('Vietnam', 'Thailand')]
PH_NAMES = [r['location'] for r in STOPS if r['country'] == 'Philippines']
ID_NAMES = [r['location'] for r in STOPS if r['country'] == 'Indonesia']
PH_HALF_NAMES = ['Manila (arrival)', 'El Nido', 'Coron']
JAVA_NAMES = ['Jakarta', 'Yogyakarta', 'Malang', 'Cemoro Lawang (Bromo)', 'Banyuwangi']
BALIG_NAMES = ['Ubud', 'Gili Trawangan', 'Gili Air', 'Canggu', 'Uluwatu']
BALI_PROPER_NAMES = ['Ubud', 'Canggu', 'Uluwatu']

# ================= 05 Confirmed Cost Base =================
ws = sheet(wb, '05 Confirmed Cost Base', STEEL)
ws.freeze_panes = 'A5'
NC = 6  # cols A..F
title(ws, 1, 1, NC, '05 · CONFIRMED COST BASE',
      'From SEA_2027_90_DAY_BUDGET.xlsx / SEA_2027_STOPS.csv / SEA_2027_LEGS.csv (checked 13 Nov 2026) · GBP per person · every scenario tab pulls from this sheet via named cells')

band(ws, 4, 1, NC, 'VIETNAM + THAILAND — LOCKED · 14 stops · 46 nights')
hdr(ws, 5, [(1,'Stop'),(2,'Dates'),(3,'Nights'),(4,'Stop £')], height=18)
r = 6
for nm in VNTH_NAMES:
    nm_, dates, n, amt = stop(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    money(ws, r, 3, n, fmt=INT); money(ws, r, 4, amt)
    r += 1
VNTH_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — VN + TH stops', bold=True, size=10)
money(ws, r, 3, f'=SUM(C6:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D6:D{r-1})', bold=True, fill=CREAM)
money(ws, r, 5, f'=D{r}/C{r}', bold=True, fill=CREAM, fmt=DGBP)
VNTH_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${VNTH_STOPS_R}"
VNTH_NIGHTS_CELL = f"'05 Confirmed Cost Base'!$C${VNTH_STOPS_R}"

r += 2
band(ws, r, 1, NC, 'CONFIRMED LEGS TRANSPORT — VN + TH (from SEA_2027_LEGS.csv)')
r += 1; leg_first = r
for desc, date, amt in legs_by_no(3,4,5,6,7,8,9,10,11,12,13):
    C(ws, r, 1, desc, size=9); C(ws, r, 2, date, size=8, align='center'); money(ws, r, 4, amt)
    r += 1
VNTH_TR_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — VN + TH transport', bold=True)
money(ws, r, 4, f'=SUM(D{leg_first}:D{r-1})', bold=True, fill=CREAM)
VNTH_TR_CELL = f"'05 Confirmed Cost Base'!$D${VNTH_TR_R}"

r += 2
band(ws, r, 1, NC, 'CONFIRMED VN + TH — ALL-IN GROUND (what the locked legs cost)')
r += 1
VNTH_ALLIN_R = r
merge_lab(ws, r, 1, 3, 'VN + TH · ALL-IN GROUND', bold=True, size=11)
money(ws, r, 4, f'=D{VNTH_STOPS_R}+D{VNTH_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
money(ws, r, 5, f'=D{r}/C{VNTH_STOPS_R}', fill=LGREENF, fmt=DGBP)
VNTH_ALLIN = f"'05 Confirmed Cost Base'!$D${VNTH_ALLIN_R}"

r += 2
band(ws, r, 1, NC, 'PHILIPPINES — FULL route · 19 nights · estimated placeholder')
r += 1
hdr(ws, r, [(1,'Stop'),(2,'Dates'),(3,'Nights'),(4,'Stop £')], height=16)
r += 1; ph_first = r
for nm in PH_NAMES:
    nm_, dates, n, amt = stop(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    money(ws, r, 3, n, fmt=INT); money(ws, r, 4, amt)
    r += 1
PH_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — PH stops', bold=True)
money(ws, r, 3, f'=SUM(C{ph_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{ph_first}:D{r-1})', bold=True, fill=CREAM)
PH_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${PH_STOPS_R}"

r += 1
band(ws, r, 1, NC, 'PHILIPPINES — transport (from legs CSV)')
r += 1; ph_tr_first = r
for desc, date, amt in legs_by_no(14,15,16,17,18,19,20,21):
    C(ws, r, 1, desc, size=9); C(ws, r, 2, date, size=8, align='center'); money(ws, r, 4, amt)
    r += 1
PH_TR_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — PH transport', bold=True)
money(ws, r, 4, f'=SUM(D{ph_tr_first}:D{r-1})', bold=True, fill=CREAM)
PH_TR_CELL = f"'05 Confirmed Cost Base'!$D${PH_TR_R}"
# remember rows of entry legs for half-PH block
PH_LEG_HKT_MNL = ph_tr_first + 0   # HKT→MNL
PH_LEG_MNL_ENI = ph_tr_first + 1   # MNL→El Nido
PH_LEG_ENI_CRN = ph_tr_first + 2   # El Nido→Coron

r += 1
band(ws, r, 1, NC, 'PHILIPPINES — ALL-IN GROUND (full 19 nights)')
r += 1
PH_ALLIN_R = r
merge_lab(ws, r, 1, 3, 'PHILIPPINES · ALL-IN GROUND', bold=True, size=11)
money(ws, r, 4, f'=D{PH_STOPS_R}+D{PH_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
money(ws, r, 5, f'=D{r}/C{PH_STOPS_R}', fill=LGREENF, fmt=DGBP)
PH_ALLIN = f"'05 Confirmed Cost Base'!$D${PH_ALLIN_R}"

r += 2
band(ws, r, 1, NC, 'PHILIPPINES — HALF route · Manila + El Nido + Coron · 10 nights · 13–23 Feb')
r += 1; phh_first = r
PH_HALF_ROWS = []
for nm in PH_HALF_NAMES:
    nm_, dates, n, amt = stop(nm)
    src = STOPS.index(next(s for s in STOPS if s['location'] == nm))
    src_row = 6 + VNTH_NAMES.index(nm) if nm in VNTH_NAMES else None
    # reference the PH full rows instead (cleaner): find PH row
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    ph_row = ph_first + PH_NAMES.index(nm)
    money(ws, r, 3, f'=C{ph_row}', fmt=INT)
    money(ws, r, 4, f'=D{ph_row}')
    PH_HALF_ROWS.append(r)
    r += 1
PHH_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — HALF PH stops', bold=True)
money(ws, r, 3, f'=SUM(C{phh_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{phh_first}:D{r-1})', bold=True, fill=CREAM)
PHH_ALLIN = f"'05 Confirmed Cost Base'!$D${r}"  # temp, overwritten below
r += 1
phh_tr_first = r
merge_lab(ws, r, 1, 2, 'Transport: HKT→MNL + MNL→El Nido + El Nido→Coron', size=8.5, color='4A4238')
money(ws, r, 4, f'=D{PH_LEG_HKT_MNL}+D{PH_LEG_MNL_ENI}+D{PH_LEG_ENI_CRN}', fill=CREAM)
PHH_TR_R = r
r += 1
PHH_ALLIN_R = r
merge_lab(ws, r, 1, 2, 'HALF PHILIPPINES · ALL-IN GROUND', bold=True, size=11)
money(ws, r, 4, f'=D{PHH_STOPS_R}+D{PHH_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
money(ws, r, 5, f'=D{r}/C{PHH_STOPS_R}', fill=LGREENF, fmt=DGBP)
PHH_ALLIN = f"'05 Confirmed Cost Base'!$D${PHH_ALLIN_R}"
PHH_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${PHH_STOPS_R}"

r += 2
band(ws, r, 1, NC, 'INDONESIA — FULL route · 25 nights · estimated placeholder')
r += 1
hdr(ws, r, [(1,'Stop'),(2,'Dates'),(3,'Nights'),(4,'Stop £')], height=16)
r += 1; id_first = r
for nm in ID_NAMES:
    nm_, dates, n, amt = stop(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    money(ws, r, 3, n, fmt=INT); money(ws, r, 4, amt)
    r += 1
ID_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — ID stops', bold=True)
money(ws, r, 3, f'=SUM(C{id_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{id_first}:D{r-1})', bold=True, fill=CREAM)
ID_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${ID_STOPS_R}"

r += 1
band(ws, r, 1, NC, 'INDONESIA — transport (from legs CSV)')
r += 1; id_tr_first = r
for desc, date, amt in legs_by_no(22,23,24,25,26,27,28,29,30,31,32,33,34,35):
    C(ws, r, 1, desc, size=9); C(ws, r, 2, date, size=8, align='center'); money(ws, r, 4, amt)
    r += 1
ID_TR_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — ID transport', bold=True)
money(ws, r, 4, f'=SUM(D{id_tr_first}:D{r-1})', bold=True, fill=CREAM)
# entry leg (MNL→CGK) is row id_tr_first; rest = subtotal − entry
ID_ENTRY_ROW = id_tr_first
ID_TR_REST_R = r + 1
merge_lab(ws, r+1, 1, 3, '… of which onward legs (excl. MNL→CGK entry)', size=8.5, color='4A4238')
money(ws, r+1, 4, f'=D{ID_TR_R}-D{ID_ENTRY_ROW}', fill=CREAM)
ID_TR_R = r
r = r + 2
ID_ALLIN_R = r
merge_lab(ws, r, 1, 3, 'INDONESIA · ALL-IN GROUND (via MNL, 4 Mar)', bold=True, size=11)
money(ws, r, 4, f'=D{ID_STOPS_R}+D{ID_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
money(ws, r, 5, f'=D{r}/C{ID_STOPS_R}', fill=LGREENF, fmt=DGBP)
ID_ALLIN = f"'05 Confirmed Cost Base'!$D${ID_ALLIN_R}"

r += 2
band(ws, r, 1, NC, 'JAVA only · Jakarta → Banyuwangi · 9 nights · 05–14 Mar')
r += 1; java_first = r
JAVA_ROWS = []
for nm in JAVA_NAMES:
    nm_, dates, n, amt = stop(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    id_row = id_first + ID_NAMES.index(nm)
    money(ws, r, 3, f'=C{id_row}', fmt=INT)
    money(ws, r, 4, f'=D{id_row}')
    JAVA_ROWS.append(r)
    r += 1
JAVA_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — Java stops', bold=True)
money(ws, r, 3, f'=SUM(C{java_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{java_first}:D{r-1})', bold=True, fill=CREAM)
JAVA_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${JAVA_STOPS_R}"
r += 1
merge_lab(ws, r, 1, 3, 'Java onward transport (excl. MNL→CGK entry)', size=8.5, color='4A4238')
money(ws, r, 4, f'=D{ID_TR_R}-D{ID_ENTRY_ROW}-D{id_tr_first+7}-D{id_tr_first+8}-D{id_tr_first+9}-D{id_tr_first+10}-D{id_tr_first+11}-D{id_tr_first+12}-D{id_tr_first+13}', fill=CREAM)
# = total ID transport minus entry minus Bali+Gili legs (29..35) => leaves 23..28 (CGK→BWG)
JAVA_TR_REST_R = r

r += 2
band(ws, r, 1, NC, 'BALI + GILIS only · skips PH & Java · 16 nights · 14–30 Mar')
r += 1; balig_first = r
BALIG_ROWS = []
for nm in BALIG_NAMES:
    nm_, dates, n, amt = stop(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    id_row = id_first + ID_NAMES.index(nm)
    money(ws, r, 3, f'=C{id_row}', fmt=INT)
    money(ws, r, 4, f'=D{id_row}')
    BALIG_ROWS.append(r)
    r += 1
BALIG_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — Bali + Gilis stops', bold=True)
money(ws, r, 3, f'=SUM(C{balig_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{balig_first}:D{r-1})', bold=True, fill=CREAM)
BALIG_STOPS_CELL = f"'05 Confirmed Cost Base'!$D${BALIG_STOPS_R}"
r += 1
band(ws, r, 1, NC, 'Bali entry & island transport (fly-in at DPS)')
r += 1
bali_entry_first = r
bali_entry = [('DPS airport → Ubud (shuttle, est.)', 5.00),
              ('Ubud → Padang Bai (Perama bus)', None),  # ref 30
              ('Padang Bai → Gili Trawangan (fast ferry)', None),  # ref 31
              ('Gili Trawangan → Gili Air (public ferry)', None),  # ref 32
              ('Gili Air → Padang Bai (fast ferry)', None),  # ref 33
              ('Padang Bai → Canggu (public bus)', None)]  # ref 34
bali_entry_map = {1: 30, 2: 31, 3: 32, 4: 33, 5: 34}
for i, (desc, est) in enumerate(bali_entry):
    C(ws, r, 1, desc, size=9)
    if est is not None:
        money(ws, r, 4, est)
    else:
        ref_leg = bali_entry_map[i]
        src = id_tr_first + (ref_leg - 22)
        money(ws, r, 4, f'=D{src}')
    r += 1
BALIG_TR_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — Bali + Gilis transport', bold=True)
money(ws, r, 4, f'=SUM(D{bali_entry_first}:D{r-1})', bold=True, fill=CREAM)
r += 1
BALIG_ALLIN_R = r
merge_lab(ws, r, 1, 2, 'BALI + GILIS · ALL-IN GROUND (excl. HKT→DPS flight)', bold=True, size=10)
money(ws, r, 4, f'=D{BALIG_STOPS_R}+D{BALIG_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
BALIG_ALLIN = f"'05 Confirmed Cost Base'!$D${BALIG_ALLIN_R}"

r += 2
band(ws, r, 1, NC, 'JUST BALI proper · Ubud + Canggu + Uluwatu · 11 nights · skips the Gilis too')
r += 1; bp_first = r
for nm in BALI_PROPER_NAMES:
    nm_, dates, n, amt = stop(nm)
    id_row = id_first + ID_NAMES.index(nm)
    C(ws, r, 1, nm_, size=9); C(ws, r, 2, dates, size=8.5, align='center')
    money(ws, r, 3, f'=C{id_row}', fmt=INT)
    money(ws, r, 4, f'=D{id_row}')
    r += 1
BALI_STOPS_R = r
merge_lab(ws, r, 1, 2, 'SUBTOTAL — Bali proper stops', bold=True)
money(ws, r, 3, f'=SUM(C{bp_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT)
money(ws, r, 4, f'=SUM(D{bp_first}:D{r-1})', bold=True, fill=CREAM)
r += 1
band(ws, r, 1, NC, 'Bali proper transport (fly-in at DPS)')
r += 1
bali_prop_tr_first = r
C(ws, r, 1, 'DPS airport → Ubud (shuttle, est.)', size=9); money(ws, r, 4, f'=D{bali_entry_first}'); r += 1
C(ws, r, 1, 'Ubud → Canggu (shuttle, est.)', size=9); money(ws, r, 4, 5.00); r += 1
C(ws, r, 1, 'Canggu → Uluwatu (local ride, est.)', size=9); money(ws, r, 4, 4.16); r += 1
BALI_TR_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — Bali proper transport', bold=True)
money(ws, r, 4, f'=SUM(D{bali_prop_tr_first}:D{r-1})', bold=True, fill=CREAM)
r += 1
BALI_ALLIN_R = r
merge_lab(ws, r, 1, 2, 'JUST BALI · ALL-IN GROUND (excl. HKT→DPS flight)', bold=True, size=10)
money(ws, r, 4, f'=D{BALI_STOPS_R}+D{BALI_TR_R}', bold=True, fill=LGREENF, fmt=GBP)
BALI_ALLIN = f"'05 Confirmed Cost Base'!$D${BALI_ALLIN_R}"

r += 2
band(ws, r, 1, NC, 'CROSS-CHECK vs your original workbook (should tie out)')
r += 1
chk = [
    ('Stops total (all 30 stays) — workbook: £4,100.10', f'=D{VNTH_STOPS_R}+D{PH_STOPS_R}+D{ID_STOPS_R}'),
    ('Transport total (36 legs) — workbook: £796.63 (ours: £796.61, 2p rounding)', f'=D{VNTH_TR_R}+D{PH_TR_R}+D{ID_TR_R}'),
    ('Confirmed VN+TH all-in — workbook: £2,454.92 ✓', f'=D{VNTH_ALLIN_R}'),
    ('PH + ID estimate — workbook: £2,441.80 ✓', f'=D{PH_STOPS_R}+D{PH_TR_R}+D{ID_STOPS_R}+D{ID_TR_R}'),
    ('Ground subtotal — workbook: £4,896.73 ✓', f'=D{VNTH_ALLIN_R}+D{PH_STOPS_R}+D{PH_TR_R}+D{ID_STOPS_R}+D{ID_TR_R}'),
]
for text, formula in chk:
    merge_lab(ws, r, 1, 4, text, size=8.5, color='4A4238')
    money(ws, r, 5, formula, fill=CREAM)
    r += 1
note(ws, r, 1, NC, 'Buffer of 8% is NOT applied on this sheet — it is applied inside each scenario tab (it protects the plan, not the locked fares). International flights are excluded from the 8% buffer, consistent with your original workbook.', height=18)
def name_ref(name, ref):
    wb.defined_names[name] = DefinedName(name, attr_text=ref)

name_ref('VNTH_ALLIN', VNTH_ALLIN)
name_ref('PH_ALLIN', PH_ALLIN)
name_ref('PHH_ALLIN', PHH_ALLIN)
name_ref('ID_ALLIN', ID_ALLIN)
name_ref('BALIG_ALLIN', BALIG_ALLIN)
name_ref('BALI_ALLIN', BALI_ALLIN)

footer(ws, r + 2, NC)
widths(ws, {'A': 46, 'B': 18, 'C': 9, 'D': 14, 'E': 13, 'F': 30})

# ================= 02 Payslip History =================
ws = sheet(wb, '02 Payslip History', STEEL)
ws.freeze_panes = 'A6'
NC = 8
title(ws, 1, 1, NC, '02 · PAYSLIP HISTORY — THE BAR JOB',
      'As supplied by you, Oct–Nov 2026 · hourly rate £12.71 · gross = hours × rate exactly (no other deductions in gross) · 30-min unpaid break excluded from rostered hours')
band(ws, 4, 1, NC, 'SEVEN WEEKS ON THE CLOCK (periods 28–34)')
hdr(ws, 5, [(1,'Period'),(2,'Week / pay date'),(3,'Hours'),(4,'Gross £'),(5,'NI @8% (>£242/wk)'),(6,'Net £ (est.)'),(7,'Check: h×12.71 − gross'),(8,'Status')], height=18)
payslips = [
    ('28', 'w/c 16 Oct · pd 16/10/26', 21.0, 266.91, 'paid'),
    ('29', 'w/c 23 Oct · pd 23/10/26', 25.5, 324.10, 'paid'),
    ('30', 'w/c 30 Oct · pd 30/10/26', 15.5, 197.00, 'paid'),
    ('31', 'w/c 06 Nov · pd 06/11/26', 26.0, 330.46, 'paid'),
    ('32', 'w/c 13 Nov · pd 13/11/26', 38.5, 489.34, 'paid'),
    ('33', 'w/c 09 Nov', 21.0, 266.91, 'OUTSTANDING'),
    ('34', 'w/c 16 Nov', 31.5, 400.37, 'OUTSTANDING'),
]
r = 6
for p, when, hrs, gross, status in payslips:
    outstanding = status == 'OUTSTANDING'
    C(ws, r, 1, p, bold=True, align='center')
    C(ws, r, 2, when, size=9, align='center')
    C(ws, r, 3, hrs, fmt='0.0', align='center')
    money(ws, r, 4, gross)
    money(ws, r, 5, f'=MAX(0,D{r}-NI_PT)*NI_RATE')
    money(ws, r, 6, f'=D{r}-E{r}')
    money(ws, r, 7, f'=ROUND(C{r}*HOURLY-D{r},2)', fmt='£0.00;[Red]-£0.00')
    C(ws, r, 8, status, bold=outstanding, size=8,
      color='B23B3B' if outstanding else '1F7A33',
      fill=LRED if outstanding else LGREENF, align='center')
    r += 1
TOT_R = r
merge_lab(ws, r, 1, 2, 'TOTAL — 7 WEEKS', bold=True, size=10)
C(ws, r, 3, f'=SUM(C6:C{r-1})', bold=True, fmt='0.0', fill=CREAM, align='center')
money(ws, r, 4, f'=SUM(D6:D{r-1})', bold=True, fill=CREAM)
money(ws, r, 5, f'=SUM(E6:E{r-1})', bold=True, fill=CREAM)
money(ws, r, 6, f'=SUM(F6:F{r-1})', bold=True, fill=CREAM)
C(ws, r, 8, '7 weeks', size=8, fill=CREAM, align='center')
r += 1
AVG_R = r
merge_lab(ws, r, 1, 2, 'WEEKLY AVERAGE (realistic)', bold=True, color='16324F')
C(ws, r, 3, f'=ROUND(C{TOT_R}/7,2)', bold=True, fmt='0.00', fill=LBLUE, align='center')
merge_lab(ws, r, 4, NC, '179 hrs ÷ 7 weeks = 25.57 h/wk — NOT the 25–35 h you hoped for yet; Christmas is the hope', size=8, color='4A4238')
AVG_HRS_CELL = f"'02 Payslip History'!$C${AVG_R}"
note(ws, r+1, 1, NC, '† Periods 33–34 are worked but not yet paid — they are added to your trip money in tab 04. Period 32 (38.5 h, £489.34) shows what a big week looks like when you get it.', height=16)
r += 3
band(ws, r, 1, NC, 'WHAT THE PAY TENDS TO LOOK LIKE')
r += 1
for txt in ['• Average week right now (25.57 h): £325 gross, NI £6.64, net £318.',
            '• 38.5 h week (period 32): £489 gross, NI £19.79, net £470.',
            '• 35 h target week (optimistic): £445 gross, NI £16.23, net £429.',
            '• 21 h quiet week: £267 gross, NI £2.00, net £265 — this is your floor until December.']:
    merge_lab(ws, r+1, 1, NC, txt, size=8.5); r += 1
footer(ws, r + 2, NC)
widths(ws, {'A': 8, 'B': 24, 'C': 10, 'D': 13, 'E': 17, 'F': 13, 'G': 18, 'H': 16})

# ================= 01 Inputs & Assumptions =================
ws = sheet(wb, '01 Inputs & Assumptions', LAMBER)
NC = 6
title(ws, 1, 1, NC, '01 · INPUTS & ASSUMPTIONS',
      'Yellow cells are yours to change — everything recalculates. Realistic = 25.57 h/wk (payslip average). Optimistic = 35 h/wk (your stated target, “will hopefully increase over Christmas”).')
band(ws, 4, 1, NC, 'THE JOB & THE PAY')
def inputrow(r, label, val, fmt, note_, name=None):
    merge_lab(ws, r, 1, 3, label, size=9.5)
    inp(ws, r, 4, val, fmt)
    merge_lab(ws, r, 5, 6, note_, size=7.5, color='4A4238')
    return val
INPUT_ROWS = {}
rows = [
    ('HOURLY_RATE', 'Hourly rate', 12.71, GBP, 'Period 28–34 all price exactly at £12.71/h'),
    ('OPT_HRS', 'Optimistic weekly hours', 35.0, '0.0', 'Your stated 25–35 h target — “hopefully increase over Christmas”'),
    ('NI_PT', 'NI Primary Threshold (per week)', 242.00, GBP, '2026/27 — gov.uk rates & thresholds (class 1, category A)'),
    ('NI_RATE', 'Employee NI rate', 0.08, PCT, '2026/27 — 8% between PT £242 and UEL £967'),
    ('PA', 'Personal allowance (2026/27)', 12570.00, GBP, 'Frozen £12,570 until Apr 2028'),
    ('PRIOR_EARN', 'Your other earnings 6 Apr–30 Sep 2026 (estimate)', 2000.00, GBP, 'Estimate only — used for the tax check in tab 03'),
]
r = 5
for name, label, val, fmt, note_ in rows:
    inputrow(r, label, val, fmt, note_); INPUT_ROWS[name] = r; r += 1
merge_lab(ws, r, 1, 3, 'Realistic weekly hours (auto from tab 02)', size=9.5)
C(ws, r, 4, f"={AVG_HRS_CELL}", bold=True, fill=CREAM, fmt='0.00', align='center')
merge_lab(ws, r, 5, 6, '25.57 — do NOT type here', size=7.5, color='4A4238'); REAL_HRS_ROW = r; r += 1

r += 1
band(ws, r, 1, NC, 'FIXED COSTS & PRE-TRIP BUY LIST')
r += 1
rows = [
    ('FIXED_M', 'Rent + phone + gym — per month (TOTAL, as you stated)', 135.00, GBP, 'Combined figure as given — confirm this really covers rent'),
    ('DAYS_DEP', 'Days from today (16 Nov) to departure (27 Dec)', 41, INT, '41 days inclusive'),
    ('INS', 'Travel insurance — buy BEFORE you fly', 200.00, GBP, 'Your pre-trip buy list'),
    ('SHOES', 'Shoes — buy BEFORE you fly', 50.00, GBP, 'Your pre-trip buy list'),
    ('TRAVEL', 'Travel cost per shift', 3.50, GBP, 'As stated'),
    ('HPS', 'Paid hours per shift (assumed)', 8.0, '0.0', '30-min unpaid break already excluded from hours'),
]
for name, label, val, fmt, note_ in rows:
    inputrow(r, label, val, fmt, note_); INPUT_ROWS[name] = r; r += 1

r += 1
band(ws, r, 1, NC, 'MONEY IN THE TANK (16 Nov 2026)')
r += 1
rows = [
    ('BAL', 'Bank balance right now', 1016.26, GBP, '“currently sat at £1,016.26”'),
    ('SAV', 'Savings', 247.00, GBP, 'Your stated £247'),
    ('BDAY', 'Birthday money (~£200)', 200.00, GBP, 'Estimate — not guaranteed'),
    ('XMA', 'Christmas money (~£200)', 200.00, GBP, 'Estimate — not guaranteed'),
    ('OJOB', 'Other job — due before departure', 150.00, GBP, 'As stated: plus £150'),
    ('OD', 'Interest-free overdraft (student account)', 1000.00, GBP, 'You said you will use it; interest-free'),
]
for name, label, val, fmt, note_ in rows:
    inputrow(r, label, val, fmt, note_); INPUT_ROWS[name] = r; r += 1

r += 1
band(ws, r, 1, NC, 'AUSTRALIA — THE NON-NEGOTIABLE END LEG')
r += 1
rows = [
    ('HOST_N', 'Nights hosted by Auntie Michelle, Lennox Head NSW', 14, INT, '1–2 weeks — her house, all living costs covered'),
    ('AU_LIVE', 'Australia living costs', 0.00, GBP, 'Hosted — you only pay the flights'),
    ('BUF', 'Buffer applied to GROUND spend (not flights)', 0.08, PCT, 'Same 8% as your original workbook'),
]
for name, label, val, fmt, note_ in rows:
    inputrow(r, label, val, fmt, note_); INPUT_ROWS[name] = r; r += 1

r += 1
band(ws, r, 1, NC, 'THE THREE RULES BAKED INTO EVERY SCENARIO')
r += 1
for txt in ['1. Australia is 100% happening - every scenario ends with Australia + a return flight BNE→Gatwick/Heathrow.',
            '2. Vietnam + Thailand are locked (paid for / non-negotiable) — every scenario includes them, re-costed at £2,454.92.',
            '3. You are never solo, EXCEPT Australia. Any scenario that strands you solo in Asia is flagged red — costed anyway because you asked.',
            'Food at home: you do not pay for your own food — home living costs are just the £135/month bundle.',
            'Week w/c 21 Dec is included even though it pays after you fly — you said that is fine.']:
    merge_lab(ws, r, 1, NC, txt, size=8.5, color='4A4238'); ws.row_dimensions[r].height = 17
    r += 1
footer(ws, r + 1, NC)
widths(ws, {'A': 34, 'B': 26, 'C': 24, 'D': 15, 'E': 26, 'F': 22})

def name_cell(name, sheet_name, cell_ref):
    wb.defined_names[name] = DefinedName(name, attr_text=f"'{sheet_name}'!{cell_ref}")

name_cell('HOURLY', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["HOURLY_RATE"]}')
name_cell('OPT_HRS', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["OPT_HRS"]}')
name_cell('REAL_HRS', '02 Payslip History', f'$C${AVG_R}')
name_cell('NI_PT', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["NI_PT"]}')
name_cell('NI_RATE', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["NI_RATE"]}')
name_cell('PA', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["PA"]}')
name_cell('PRIOR_EARN', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["PRIOR_EARN"]}')
name_cell('FIXED_M', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["FIXED_M"]}')
name_cell('DAYS_DEP', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["DAYS_DEP"]}')
name_cell('INS', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["INS"]}')
name_cell('SHOES', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["SHOES"]}')
name_cell('TRAVEL', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["TRAVEL"]}')
name_cell('HPS', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["HPS"]}')
name_cell('BAL', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["BAL"]}')
name_cell('SAV', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["SAV"]}')
name_cell('BDAY', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["BDAY"]}')
name_cell('XMA', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["XMA"]}')
name_cell('OJOB', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["OJOB"]}')
name_cell('OD', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["OD"]}')
name_cell('HOST_N', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["HOST_N"]}')
name_cell('AU_LIVE', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["AU_LIVE"]}')
name_cell('BUF', '01 Inputs & Assumptions', f'$D${INPUT_ROWS["BUF"]}')

# ================= 03 UK Earnings Model =================
ws = sheet(wb, '03 UK Earnings Model', STEEL)
ws.freeze_panes = 'A5'
NC = 10
title(ws, 1, 1, NC, '03 · UK EARNINGS MODEL — OCT → 27 DEC 2026',
      'Income tax + National Insurance applied (2026/27, rUK rates). Pension not deducted — if auto-enrolled & not opted out, knock ~3–5% off the net figures.')

band(ws, 4, 1, NC, 'A · EARNED, NOT YET PAID — periods 33 & 34 (w/c 09 / w/c 16 Nov)')
hdr(ws, 5, [(1,'Period'),(2,'Week'),(3,'Hours'),(4,'Gross £'),(5,'NI @8% >£242'),(6,'Net £')], height=16)
r = 6
OUT_ROWS = [11, 12]  # rows in tab 02
C(ws, r, 1, '33', align='center', bold=True); C(ws, r, 2, 'w/c 09 Nov', size=9, align='center')
C(ws, r, 3, f"='02 Payslip History'!C{OUT_ROWS[0]}", fmt='0.0', align='center')
C(ws, r, 4, f"='02 Payslip History'!D{OUT_ROWS[0]}", fmt=GBP)
C(ws, r, 5, f"=MAX(0,D{r}-NI_PT)*NI_RATE", fmt=GBP); C(ws, r, 6, f"=D{r}-E{r}", fmt=GBP)
r += 1
C(ws, r, 1, '34', align='center', bold=True); C(ws, r, 2, 'w/c 16 Nov', size=9, align='center')
C(ws, r, 3, f"='02 Payslip History'!C{OUT_ROWS[1]}", fmt='0.0', align='center')
C(ws, r, 4, f"='02 Payslip History'!D{OUT_ROWS[1]}", fmt=GBP)
C(ws, r, 5, f"=MAX(0,D{r}-NI_PT)*NI_RATE", fmt=GBP); C(ws, r, 6, f"=D{r}-E{r}", fmt=GBP)
r += 1
A_SUB_R = r
merge_lab(ws, r, 1, 3, 'SUBTOTAL — outstanding pay', bold=True)
money(ws, r, 4, f'=SUM(D6:D{r-1})', bold=True, fill=CREAM)
money(ws, r, 5, f'=SUM(E6:E{r-1})', bold=True, fill=CREAM)
money(ws, r, 6, f'=SUM(F6:F{r-1})', bold=True, fill=LGREENF)
NET_OUT_CELL = f"'03 UK Earnings Model'!$F${A_SUB_R}"

r += 2
band(ws, r, 1, NC, 'B · FIVE WEEKS LEFT — w/c 23 Nov → w/c 21 Dec (week w/c 21 Dec pays after you fly — you said that is fine)')
r += 1
hdr(ws, r, [(1,'Week'),(2,'Hrs · realistic'),(3,'Gross £'),(4,'NI £'),(5,'Net £'),(6,'Hrs · optimistic'),(7,'Gross £'),(8,'NI £'),(9,'Net £'),(10,'Note')], height=16)
FUT_FIRST = r + 1
weeks = ['23 Nov', '30 Nov', '07 Dec', '14 Dec', '21 Dec †']
r = FUT_FIRST
for wk in weeks:
    C(ws, r, 1, 'w/c ' + wk, size=9, align='center')
    C(ws, r, 2, '=REAL_HRS', fmt='0.00', align='center')
    C(ws, r, 3, f'=B{r}*HOURLY', fmt=GBP)
    C(ws, r, 4, f'=MAX(0,C{r}-NI_PT)*NI_RATE', fmt=GBP)
    C(ws, r, 5, f'=C{r}-D{r}', fmt=GBP)
    C(ws, r, 6, '=OPT_HRS', fmt='0.0', align='center')
    C(ws, r, 7, f'=F{r}*HOURLY', fmt=GBP)
    C(ws, r, 8, f'=MAX(0,G{r}-NI_PT)*NI_RATE', fmt=GBP)
    C(ws, r, 9, f'=G{r}-H{r}', fmt=GBP)
    if wk.startswith('21'): C(ws, r, 10, 'paid after you fly', size=8, color='B23B3B')
    r += 1
FUT_TOT_R = r
merge_lab(ws, r, 1, 1, 'TOTAL', bold=True, size=10)
C(ws, r, 2, f'=SUM(B{FUT_FIRST}:B{r-1})', bold=True, fill=CREAM, fmt='0.0', align='center')
for col in ['C','D','E','G','H','I']:
    money(ws, r, ord(col)-64, f'=SUM({col}{FUT_FIRST}:{col}{r-1})', bold=True, fill=CREAM)
merge_lab(ws, r, 6, 6, '', size=8)
NET_FUT_REAL_CELL = f"'03 UK Earnings Model'!$E${FUT_TOT_R}"
NET_FUT_OPT_CELL = f"'03 UK Earnings Model'!$I${FUT_TOT_R}"
GROSS_FUT_REAL_CELL = f"'03 UK Earnings Model'!$C${FUT_TOT_R}"
GROSS_FUT_OPT_CELL = f"'03 UK Earnings Model'!$G${FUT_TOT_R}"
note(ws, r+1, 1, NC, 'Realistic = your payslip average (25.57 h/wk, £325/wk gross). Optimistic = 35 h/wk (£445/wk gross) — your stated target with Christmas coming. Each shift carries £3.50 travel; total travel is deducted in tab 04.', height=16)

r = FUT_TOT_R + 3
band(ws, r, 1, NC, 'C · INCOME TAX — the cumulative check (rUK rates, £12,570 personal allowance)')
r += 1
tax_rows = [
    ('Bar gross earned to date (periods 28–34, incl. outstanding)', "='02 Payslip History'!$D$13", GBP, False),
    ('… plus future 5 weeks (realistic)', f'={GROSS_FUT_REAL_CELL}', GBP, False),
    ('… plus future 5 weeks (optimistic)', f'={GROSS_FUT_OPT_CELL}', GBP, False),
    ('… plus other job (PR 33-ish timing not needed — flat £150)', '=OJOB', GBP, False),
    ('… plus prior earnings Apr–Sep 2026 (your estimate, tab 01)', '=PRIOR_EARN', GBP, False),
]
CUM_REAL_R = r + len(tax_rows) + 1
CUM_OPT_R = CUM_REAL_R + 1
for label, formula, fmt, _ in tax_rows:
    merge_lab(ws, r, 1, 4, label, size=9); money(ws, r, 5, formula, fmt=fmt); r += 1
merge_lab(ws, r, 1, 4, 'CUMULATIVE TAXABLE INCOME — realistic', bold=True)
money(ws, r, 5, f"='02 Payslip History'!$D$13+{GROSS_FUT_REAL_CELL}+OJOB+PRIOR_EARN", bold=True, fill=LBLUE); r += 1
merge_lab(ws, r, 1, 4, 'CUMULATIVE TAXABLE INCOME — optimistic', bold=True)
money(ws, r, 5, f"='02 Payslip History'!$D$13+{GROSS_FUT_OPT_CELL}+OJOB+PRIOR_EARN", bold=True, fill=LBLUE); r += 1
merge_lab(ws, r, 1, 4, 'Headroom under £12,570 — realistic / optimistic', size=9, color='4A4238')
money(ws, r, 5, f"=PA-('02 Payslip History'!$D$13+{GROSS_FUT_REAL_CELL}+OJOB+PRIOR_EARN)", fill=CREAM)
C(ws, r, 7, f"=PA-('02 Payslip History'!$D$13+{GROSS_FUT_OPT_CELL}+OJOB+PRIOR_EARN)", fmt=GBP, border=BOX, align='center'); r += 1
merge_lab(ws, r, 1, 4, 'INCOME TAX DUE (rUK, 20% over PA) — realistic / optimistic', bold=True, color='16324F')
money(ws, r, 5, f"=MAX(0,('02 Payslip History'!$D$13+{GROSS_FUT_REAL_CELL}+OJOB+PRIOR_EARN)-PA)*0.2", bold=True, fill=LGREENF)
C(ws, r, 7, f"=MAX(0,('02 Payslip History'!$D$13+{GROSS_FUT_OPT_CELL}+OJOB+PRIOR_EARN)-PA)*0.2", fmt=GBP, bold=True, fill=LGREENF, align='center', border=BOX)
r += 1
note(ws, r, 1, NC, '£0 tax unless your OTHER earnings Apr–Sep top roughly £8,400 (realistic) or £7,800 (optimistic). If they do: each extra £1,000 costs £200 tax. Student loan: nothing deducted below £25k-ish thresholds either way. NI is charged weekly above £242 regardless of cumulative position.', height=26)

r += 2
band(ws, r, 1, NC, 'D · WHAT ACTUALLY LANDS BY 27 DEC')
r += 1
for label, formula, fmt in [
    ('Net already received this run (periods 28–32 — inside your £1,016.26)', "='02 Payslip History'!$F$13-'02 Payslip History'!F11-'02 Payslip History'!F12", GBP),
    ('Outstanding periods 33–34 (net)', f'={NET_OUT_CELL}', GBP),
    ('Future weeks (net) — realistic', f'={NET_FUT_REAL_CELL}', GBP),
    ('Future weeks (net) — optimistic', f'={NET_FUT_OPT_CELL}', GBP),
]:
    merge_lab(ws, r, 1, 4, label, size=9); money(ws, r, 5, formula, fmt=fmt); r += 1
note(ws, r, 1, NC, 'Notice the honest asymmetry: your balance £1,016.26 already contains periods 28–32 net of NI/tax. We add outstanding + future only — never the same money twice.', height=16)
footer(ws, r + 2, NC)
widths(ws, {'A': 34, 'B': 13, 'C': 13, 'D': 13, 'E': 13, 'F': 15, 'G': 14, 'H': 12, 'I': 13, 'J': 24})
name_cell('NET_OUT', '03 UK Earnings Model', f'$F${A_SUB_R}')
name_cell('NET_FUT_REAL', '03 UK Earnings Model', f'$E${FUT_TOT_R}')
name_cell('NET_FUT_OPT', '03 UK Earnings Model', f'$I${FUT_TOT_R}')
name_cell('GROSS_FUT_REAL', '03 UK Earnings Model', f'$C${FUT_TOT_R}')
name_cell('GROSS_FUT_OPT', '03 UK Earnings Model', f'$G${FUT_TOT_R}')

# ================= 04 Funds Available =================
ws = sheet(wb, '04 Funds Available', ORANGE)
NC = 7
title(ws, 1, 1, NC, '04 · FUNDS AVAILABLE — HOW FAR YOUR MONEY GOES',
      'Realistic (25.57 h/wk) vs Optimistic (35 h/wk) · then vs FULL interest-free overdraft · then if birthday/Christmas never land. Yellow none here — change tab 01 instead.')
band(ws, 4, 1, NC, 'PART 1 — CASH IN HAND BY DEPARTURE')
hdr(ws, 5, [(1,'Source'),(2,'£ — realistic'),(3,'£ — optimistic')], height=14)
r = 6
cash_rows = [
    ('Bank balance today (16 Nov 2026)', '=BAL', '=BAL'),
    ('Savings', '=SAV', '=SAV'),
    ('Birthday money (~£200, not guaranteed)', '=BDAY', '=BDAY'),
    ('Christmas money (~£200, not guaranteed)', '=XMA', '=XMA'),
    ('Other job, this timeframe', '=OJOB', '=OJOB'),
    ('Outstanding bar pay, periods 33–34 (net)', '=NET_OUT', '=NET_OUT'),
    ('Future 5 weeks bar pay (net)', '=NET_FUT_REAL', '=NET_FUT_OPT'),
]
for label, fa, fb in cash_rows:
    merge_lab(ws, r, 1, 1, label, size=9)
    money(ws, r, 2, fa); money(ws, r, 3, fb)
    r += 1
P1_SUB_R = r
merge_lab(ws, r, 1, 1, 'GROSS CASH AVAILABLE', bold=True, size=10, color='16324F')
money(ws, r, 2, f'=SUM(B6:B{r-1})', bold=True, fill=CREAM)
money(ws, r, 3, f'=SUM(C6:C{r-1})', bold=True, fill=CREAM)
r += 2
band(ws, r, 1, NC, 'PART 2 — SPEND BEFORE YOU FLY (Nov 16 → 27 Dec)')
r += 1
pre_rows = [
    ('Travel insurance', '=INS', '=INS'),
    ('Shoes', '=SHOES', '=SHOES'),
    ('Rent + phone + gym (41 days @ £135/month)', '=FIXED_M*DAYS_DEP/30.44', '=FIXED_M*DAYS_DEP/30.44'),
    ('Shift travel (£3.50 · shift = 8 paid hrs)', '=REAL_HRS*5/HPS*TRAVEL', '=OPT_HRS*5/HPS*TRAVEL'),
]
for label, fa, fb in pre_rows:
    merge_lab(ws, r, 1, 1, label, size=9)
    money(ws, r, 2, fa); money(ws, r, 3, fb)
    r += 1
P2_SUB_R = r
merge_lab(ws, r, 1, 1, 'SPEND BEFORE DEPARTURE', bold=True, size=10, color='16324F')
money(ws, r, 2, f'=SUM(B{r-len(pre_rows)}:B{r-1})', bold=True, fill=LRED)
money(ws, r, 3, f'=SUM(C{r-len(pre_rows)}:C{r-1})', bold=True, fill=LRED)
r += 2
band(ws, r, 1, NC, 'PART 3 — YOUR TRIP ENVELOPE (what the scenarios in tab 07 are measured against)')
r += 1
ENV_A_R = r
merge_lab(ws, r, 1, 1, 'TRIP ENVELOPE — no overdraft', bold=True, size=10, color='16324F')
money(ws, r, 2, f'=B{P1_SUB_R}-B{P2_SUB_R}', bold=True, fill=LGREENF, fmt=GBP)
money(ws, r, 3, f'=C{P1_SUB_R}-C{P2_SUB_R}', bold=True, fill=LGREENF, fmt=GBP)
r += 1
merge_lab(ws, r, 1, 1, '+ Interest-free overdraft if fully used', size=9)
money(ws, r, 2, '=OD'); money(ws, r, 3, '=OD')
r += 1
ENV_C_R = r
merge_lab(ws, r, 1, 1, 'TRIP ENVELOPE — MAX overdraft (£1,000 student)', bold=True, size=10, color='16324F')
money(ws, r, 2, f'=B{ENV_A_R}+OD', bold=True, fill=LBLUE, fmt=GBP)
money(ws, r, 3, f'=C{ENV_A_R}+OD', bold=True, fill=LBLUE, fmt=GBP)
r += 1
ENV_E_R = r
merge_lab(ws, r, 1, 1, 'WORST CASE — birthday & Christmas never land (no OD)', size=9, color='B23B3B')
money(ws, r, 2, f'=B{ENV_A_R}-BDAY-XMA', fill=LAMBER); money(ws, r, 3, f'=C{ENV_A_R}-BDAY-XMA', fill=LAMBER)
r += 1
merge_lab(ws, r, 1, 1, 'WORST CASE — birthday & Christmas never land (max OD)', size=9, color='B23B3B')
money(ws, r, 2, f'=B{ENV_E_R}+OD', fill=LAMBER); money(ws, r, 3, f'=C{ENV_E_R}+OD', fill=LAMBER)
r += 1

for col, cellref in [('B', f'$B${ENV_A_R}'), ('C', f'$C${ENV_A_R}')]:
    pass
name_cell('ENV_A', '04 Funds Available', f'$B${ENV_A_R}')
name_cell('ENV_B', '04 Funds Available', f'$C${ENV_A_R}')
name_cell('ENV_C', '04 Funds Available', f'$B${ENV_C_R}')
name_cell('ENV_D', '04 Funds Available', f'$C${ENV_C_R}')
name_cell('ENV_E', '04 Funds Available', f'$B${ENV_E_R}')
name_cell('ENV_F', '04 Funds Available', f'$C${ENV_E_R}')

r += 1
band(ws, r, 1, NC, 'PART 4 — READING THE NUMBERS (as it is)')
r += 1
for txt in [
    '• NI on your October–December bar earnings ≈ £49 in total. Income tax: £0 while cumulative income stays under £12,570 — headroom ≈ £8,300 realistic.',
    '• £1,016.26 already contains your October wages — do not count it twice. We add outstanding (£667.28 gross) + future weeks only.',
    '• Your rent/phone/gym figure is taken literally as £135 TOTAL per month — if that is wrong, every envelope moves.',
    '• Birthday and Christmas money are hopes, not facts — tab 07 shows scenarios against the worst-case envelopes too.',
    '• The £1,000 overdraft is interest-free, BUT: every £1 of it is a £1 you owe the second you land home. Treat ENV_A/ENV_B as the plan; ENV_C/ENV_D as the ceiling.',
    '• £3.50 per shift travel × ~16 shifts (realistic) / ~22 shifts (optimistic) is already deducted.',
    '• If your pension is auto-enrolled and you have not opted out, net pay falls ~3–5% — realistic headroom drops by roughly another £50–£89.',
]:
    merge_lab(ws, r, 1, NC, txt, size=8.5, color='4A4238'); ws.row_dimensions[r].height = 17
    r += 1
footer(ws, r + 1, NC)
widths(ws, {'A': 56, 'B': 17, 'C': 17, 'D': 18, 'E': 10, 'F': 10, 'G': 10})

# ================= 06 Flight Research =================
ws = sheet(wb, '06 Flight Research', ORANGE)
NC = 7
title(ws, 1, 1, NC, '06 · FLIGHT RESEARCH — checked 16 Nov 2026',
      'One-way, economy, no checked bag unless stated · USD→GBP ≈ 0.78 · AUD→GBP ≈ 0.49 · THB→GBP ≈ 0.021 · PHP/IDR per your workbook · named cells feed the scenarios')
hdr(ws, 4, [(1,'Route'),(2,'Used in'),(3,'Date'),(4,'Est £'),(5,'Range seen £'),(6,'Source (checked Nov 2026)'),(7,'Notes')], height=18)
FL_FIRST = 5
flights = [
    ('LGW → HAN — one-way · LONDON GATWICK', 'LOCKED — already booked', '27 Dec 26', None, 'PAID', 'Your booking', 'LGW→Hanoi is excluded from every envelope — it is already bought'),
    ('SGN → BKK — Vietjet direct', 'Vietnam → Thailand bridge', '22 Jan 27', 60.00, '55–70', 'Google Flights card dated 22 Jan 2027 (via your workbook, leg 7)', 'In the locked £2,454.92'),
    ('HKT → MNL — Vietjet, 1 stop', 'PHILIPPINES bridge (13 Feb)', '12 Feb 27', 137.00, '120–160', 'Google Flights card dated 12 Feb 2027 (via your workbook, leg 14)', 'The bridge into the estimate — book early'),
    ('MNL → ENI — Cebgo via CEB', 'Philippines', '14 Feb 27', 168.00, '150–190', 'Google Flights dated (via your workbook, leg 15)', 'First safe connection after 05:30 arrival'),
    ('USU → IAO — PAL via CEB', 'Philippines', '23 Feb 27', 73.00, '60–90', 'Google Flights dated (via your workbook, leg 17)', ''),
    ('IAO → CEB → Moalboal — Sunlight + Ceres', 'Philippines', '28 Feb 27', 32.50, '30–35', 'Via your workbook, legs 18–19', ''),
    ('CEB → MNL — AirAsia direct', 'Philippines exit', '03 Mar 27', 27.00, '25–35', 'Google Flights dated (via your workbook, leg 21)', ''),
    ('HKT → BNE — 1 stop (SIN/KUL/MNL)', 'S1 · THAI exit straight to Australia', '13 Feb 27', 195.00, '180–210', 'Expedia $266 · Skyscanner $235–246 · Trip.com $234 one-way', 'THIS IS THE CHEAPEST WAY TO AUSTRALIA — book by mid-Jan'),
    ('USU → MNL — PAL / CebuPac', 'S2 · half-PH exit (13–23 Feb)', '23 Feb 27', 60.00, '50–115', 'PAL USU→MNL from PHP 4,160 all-in · Skyscanner US$65 · Kayak $75 · eDreams ~$110 avg', 'Short hop back to Manila to catch BNE'),
    ('MNL → BNE — 1 stop (SIN/MNL)', 'S2 · S3 · PH exit to Australia', '23 Feb / 04 Mar 27', 190.00, '152–260', 'Skyscanner $198 (lowest seen) · Travelocity PAL $334 · Expedia $392 typ. · KAYAK $346', 'Cheapest in March per KAYAK — $686 RT'),
    ('HKT → CGK — 1 stop (Scoot/SQ)', 'S4 only · skip-PH, meet friends Jakarta', '04 Mar 27', 95.00, '85–102', 'Skyscanner $111–131 · Traveloka $111 · cheapflights.com ฿3,097', 'Flag: your no-solo rule makes this illegal for you — see S4'),
    ('HKT → DPS — AirAsia direct', 'S5 · S6 · Bali entry', '~14 Mar 27', 80.00, '62–95', 'Skyscanner $81 · KAYAK $92 · Google Flights $90 · Trip.com $84 · Traveloka $78', 'Non-stop Phuket→Denpasar exists (Indonesia AirAsia)'),
    ('Banyuwangi → SUB — bus/train', 'S7 · S9 · Java exit ground', '14 Mar 27', 8.00, '6–12', 'Public intercity bus ~£6 (your workbook, leg 28) · train alt ~£8', 'Then SUB→BNE'),
    ('SUB → BNE — 1 stop (SIN, AirAsia)', 'S7 · S9 · Java exit to Australia', '14 Mar 27', 165.00, '140–215', 'Skyscanner $217 · Trip.com $184 · AirAsia 1-stop SIN 11h45', 'No direct SUB→BNE — via SIN'),
    ('DPS → BNE — 1 stop', 'S4 · S5 · S6 · S8 · FULL-route exit', '30 Mar 27', 150.00, '125–165', 'Expedia $165 · BatikAir direct $184 (Mar 5) · workbook said £182 (check again)', 'BatikAir Malaysia BNE–DPS direct exists — try direct'),
    ('BNE → LHR — 1 stop (PER/SIN/DXB/HKG)', 'RETURN FLIGHT — every scenario · arrival ~2 wks after AU entry', 'varies by scenario', 840.00, '380–1,100', 'idealo routes BNE–LHR £836 (01 Feb 2027) · Virgin Australia Mar-27 AUD 2,275 / Apr-27 AUD 1,934 · Cathay AUD 2,057 · Skyscanner $378 lowest-seen', 'RE-CHECK THIS FARE Dec–Jan — it is the single biggest swing factor in every scenario'),
    ('DPS → LON — 1 stop 18h35', 'memo — NOT allowed by your rules', '30 Mar 27', 414.00, '400–450', 'Your workbook estimate', 'Cheaper! But it skips Australia. Noted for completeness, never used'),
    ('eVisitor (subclass 651) — UK passport', 'All Australia legs', 'before flying', 0.00, '0', 'homeaffairs.gov.au', 'FREE · 90-day stay · enough for 1–2 weeks hosted'),
    ('Working Holiday Visa (417)', 'ONLY if you decide to WORK in Australia', 'before flying', 345.00, '330–355', 'homeaffairs.gov.au', 'NOT needed for a hosted 1–2 week visit — 651 is enough'),
]
r = FL_FIRST
FLIGHT_CELLS = {}
named_flight = {
    'HKT → BNE — 1 stop (SIN/KUL/MNL)': 'FLIGHT_HKT_BNE',
    'USU → MNL — PAL / CebuPac': 'FLIGHT_USU_MNL',
    'MNL → BNE — 1 stop (SIN/MNL)': 'FLIGHT_MNL_BNE',
    'HKT → CGK — 1 stop (Scoot/SQ)': 'FLIGHT_HKT_CGK',
    'HKT → DPS — AirAsia direct': 'FLIGHT_HKT_DPS',
    'Banyuwangi → SUB — bus/train': 'GND_BWG_SUB',
    'SUB → BNE — 1 stop (SIN, AirAsia)': 'FLIGHT_SUB_BNE',
    'DPS → BNE — 1 stop': 'FLIGHT_DPS_BNE',
    'BNE → LHR — 1 stop (PER/SIN/DXB/HKG)': 'FLIGHT_BNE_LHR',
}
for route, used, date, est, rng, src, nt in flights:
    C(ws, r, 1, route, size=8.5, bold=True)
    C(ws, r, 2, used, size=8)
    C(ws, r, 3, date, size=8, align='center')
    if est is not None:
        money(ws, r, 4, est)
    else:
        C(ws, r, 4, 'PAID', bold=True, size=8, color='1F7A33', align='center')
    C(ws, r, 5, rng, size=8, align='center')
    C(ws, r, 6, src, size=7.5, wrap=True)
    C(ws, r, 7, nt, size=7.5, wrap=True, color='4A4238')
    if route in named_flight:
        FLIGHT_CELLS[named_flight[route]] = f"'06 Flight Research'!$D${r}"
    ws.row_dimensions[r].height = 30
    r += 1
for nm, ref in FLIGHT_CELLS.items():
    name_cell(nm, '06 Flight Research', ref.split('!')[1])
r += 1
note(ws, r, 1, NC, 'Cheapest exit dates (ranked by total cost, not fare): 13 Feb HKT→BNE £195 wins — the £35 saving vs DPS is noise next to £320/week of ground spend. BNE→LHR at £840 = ~£60/day of your whole trip budget. All fares move — re-check HKT→BNE and BNE→LHR in mid-December and before you commit.', height=26)
footer(ws, r + 2, NC)
widths(ws, {'A': 36, 'B': 26, 'C': 14, 'D': 10, 'E': 11, 'F': 52, 'G': 46})

# ================= scenario tabs builder =================
def r05(row, col):
    return f"'05 Confirmed Cost Base'!${col}${row}"

ID_ALLIN_FROM_HKT = f"={r05(ID_STOPS_R,'D')}+({r05(ID_TR_R,'D')}-{r05(ID_ENTRY_ROW,'D')})+FLIGHT_HKT_CGK"
JAVA_ALLIN_MNL = f"={r05(JAVA_STOPS_R,'D')}+{r05(JAVA_TR_REST_R,'D')}+{r05(ID_ENTRY_ROW,'D')}"

def build_scenario(code, title_text, legal, legal_detail, route_rows, cost_lines, flight_lines,
                   gap_lines, au_text, notes, verdict_legal_ok=True):
    """route_rows: list of (label, dates, nights_formula_or_int, amt_formula_or_None)
       cost_lines: list of (label, formula)  -> part of GROUND (buffer applies)
       flight_lines: list of (label, formula) -> NOT buffered
       gap_lines: list of (label, formula)    -> included in GROUND
    """
    ws = sheet(wb, code, NAVY)
    NC = 7
    title(ws, 1, 1, NC, f'{code} · {title_text}', legal_detail)
    # ---- legality banner
    if legal == 'YES':
        band(ws, 4, 1, NC, '✓ GROUP-LEGAL — you are with the lads until you permanently leave for Australia')
        ws.row_dimensions[4].height = 18
    else:
        ws.merge_cells(start_row=4, start_column=1, end_row=4, end_column=NC)
        C(ws, 4, 1, '✗ NOT GROUP-LEGAL — ' + legal_detail, bold=True, size=9, color='FFFFFF', fill='B23B3B', align='left')
        ws.row_dimensions[4].height = 18

    band(ws, 6, 1, NC, 'A · THE ROUTE (locked legs first, then your call)')
    hdr(ws, 7, [(1,'Stage'),(2,'Dates'),(3,'Nights'),(4,'Ground £')], height=15)
    r = 8
    route_first = r
    for label, dates, nights, amt in route_rows:
        C(ws, r, 1, label, size=8.5, wrap=True)
        C(ws, r, 2, dates, size=8, align='center')
        if isinstance(nights, str):
            C(ws, r, 3, nights, fmt=INT, align='center')
        else:
            C(ws, r, 3, nights, fmt=INT, align='center')
        if amt is not None:
            money(ws, r, 4, amt)
        else:
            C(ws, r, 4, '—', size=8, align='center', color='9A9184')
        r += 1
    ROUTE_TOT_R = r
    merge_lab(ws, r, 1, 2, 'TOTAL TRIP', bold=True, size=10, color='16324F')
    C(ws, r, 3, f'=SUM(C{route_first}:C{r-1})', bold=True, fill=CREAM, fmt=INT, align='center')
    C(ws, r, 4, 'see build →', size=8, italic=True, color='9A9184', align='center', border=None)
    NC_A = NC

    r += 2
    band(ws, r, 1, NC_A, 'B · THE COST BUILD (per person · locked + your legs + Australia)')
    r += 1
    cost_first = r
    for label, formula in cost_lines:
        merge_lab(ws, r, 1, 3, label, size=9, wrap=True)
        money(ws, r, 4, formula, fmt=GBP)
        r += 1
    for label, formula in gap_lines:
        merge_lab(ws, r, 1, 3, label, size=9, wrap=True)
        money(ws, r, 4, formula, fmt=GBP)
        ws.cell(row=r, column=4).fill = PatternFill('solid', fgColor=LAMBER)
        r += 1
    G_SUB_R = r
    merge_lab(ws, r, 1, 3, 'GROUND SUBTOTAL (locked + chosen legs + any solo gap)', bold=True, size=9.5)
    money(ws, r, 4, f'=SUM(D{cost_first}:D{r-1})', bold=True, fill=CREAM)
    r += 1
    BUF_R = r
    merge_lab(ws, r, 1, 3, 'Ground buffer @ 8% (flights excluded — same as your workbook)', size=9)
    money(ws, r, 4, f'=D{G_SUB_R}*BUF', fmt=GBP)
    r += 1
    FL_FIRST_R = r
    for label, formula in flight_lines:
        merge_lab(ws, r, 1, 3, label, size=9, wrap=True)
        money(ws, r, 4, formula, fmt=GBP)
        r += 1
    RET_R = r
    merge_lab(ws, r, 1, 3, 'Australia → Gatwick/Heathrow — RETURN (1 stop)', size=9)
    money(ws, r, 4, '=FLIGHT_BNE_LHR', fmt=GBP)
    r += 1
    AU_R = r
    merge_lab(ws, r, 1, 3, 'Australia living — auntie hosts you, Lennox Head (14 nights)', size=9)
    money(ws, r, 4, '=AU_LIVE', fmt=GBP)
    r += 1
    TOTAL_R = r
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    C(ws, r, 1, 'SCENARIO TOTAL', bold=True, size=13, color='FFFFFF', fill=NAVY, align='left')
    money(ws, r, 4, f'=D{G_SUB_R}*(1+BUF)+SUM(D{FL_FIRST_R}:D{RET_R})+D{AU_R}', bold=True, fill=NAVY, fmt=GBP)
    ws.row_dimensions[r].height = 26
    ws.cell(row=r, column=4).font = Font(name='Calibri', bold=True, size=13, color='FFFFFF')

    r += 2
    band(ws, r, 1, NC_A, 'C · CAN YOU AFFORD IT? (against tab 04 envelopes)')
    r += 1
    env_rows = [('A · Realistic hours, NO overdraft', 'ENV_A'), ('B · Optimistic hours, NO overdraft', 'ENV_B'),
                ('C · Realistic hours + FULL £1,000 interest-free overdraft', 'ENV_C'),
                ('D · Optimistic hours + FULL £1,000 interest-free overdraft', 'ENV_D')]
    ENV_REM_ROWS = []
    for label, env in env_rows:
        merge_lab(ws, r, 1, 3, label, size=9)
        money(ws, r, 4, f'={env}-D{TOTAL_R}', fmt='£#,##0.00;[Red]-£#,##0.00')
        ENV_REM_ROWS.append(r)
        if r % 2 == 0:
            for c_ in range(1, NC_A + 1):
                if ws.cell(row=r, column=c_).fill.fgColor.rgb == '00000000':
                    ws.cell(row=r, column=c_).fill = PatternFill('solid', fgColor=CREAM)
        r += 1
    VERDICT_R = r
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=NC_A)
    C(ws, r, 1, f'=IF(D{TOTAL_R}<=ENV_A,"✓ FUNDED — realistic hours, no overdraft needed",IF(D{TOTAL_R}<=ENV_B,"✓ FUNDED — but only if December delivers 35 h/wk (no overdraft)",IF(D{TOTAL_R}<=ENV_C,"⚠ TIGHT — needs the full £1,000 interest-free overdraft on top of realistic hours",IF(D{TOTAL_R}<=ENV_D,"⚠ BARELY — optimistic hours AND the full overdraft, and hope flights don’t move","✗ CANNOT BE FUNDED — not even optimistic hours + max overdraft"))))',
      bold=True, size=10, color='16324F', fill=LGREENF, align='left', wrap=True)
    ws.row_dimensions[r].height = 24
    from openpyxl.formatting.rule import FormulaRule
    _rng = f'A{VERDICT_R}:G{VERDICT_R}'
    ws.conditional_formatting.add(_rng, FormulaRule(formula=[f'$D${TOTAL_R}>ENV_D'], fill=PatternFill('solid', bgColor='FAE3E3')))
    ws.conditional_formatting.add(_rng, FormulaRule(formula=[f'AND($D${TOTAL_R}>ENV_C,$D${TOTAL_R}<=ENV_D)'], fill=PatternFill('solid', bgColor='FDEBD0')))
    ws.conditional_formatting.add(_rng, FormulaRule(formula=[f'$D${TOTAL_R}<=ENV_C'], fill=PatternFill('solid', bgColor='D8EFDD')))

    r += 2
    band(ws, r, 1, NC_A, 'D · NOTES & FINE PRINT')
    r += 1
    for n_ in notes:
        merge_lab(ws, r, 1, NC_A, n_, size=8.5, color='4A4238', wrap=True)
        ws.row_dimensions[r].height = 26
        r += 1
    footer(ws, r + 1, NC_A)
    widths(ws, {'A': 34, 'B': 20, 'C': 12, 'D': 15, 'E': 18, 'F': 24, 'G': 28})
    return {
        'code': code, 'legal': legal, 'route_first': route_first, 'route_tot': ROUTE_TOT_R,
        'ground_sub': G_SUB_R, 'buffer': BUF_R, 'total': TOTAL_R,
        'rem_A': ENV_REM_ROWS[0], 'rem_B': ENV_REM_ROWS[1], 'rem_C': ENV_REM_ROWS[2], 'rem_D': ENV_REM_ROWS[3],
        'verdict': VERDICT_R,
        'asia_nights': f'=C{ROUTE_TOT_R}-HOST_N',
    }

VN_R, TH_R = (6, 12), (13, 19)
LOCKED_ROWS = [
    ('LOCKED · Vietnam — 7 stops', '28 Dec – 22 Jan', f"=SUM('05 Confirmed Cost Base'!C{VN_R[0]}:C{VN_R[1]})", f"=SUM('05 Confirmed Cost Base'!D{VN_R[0]}:D{VN_R[1]})"),
    ('LOCKED · Thailand — 7 stops', '22 Jan – 12 Feb', f"=SUM('05 Confirmed Cost Base'!C{TH_R[0]}:C{TH_R[1]})", f"=SUM('05 Confirmed Cost Base'!D{TH_R[0]}:D{TH_R[1]})"),
]
LOCKED_COST = [('LOCKED · Vietnam + Thailand — stops + transport', '=VNTH_ALLIN')]

def ph_rows():
    return [(f"Philippines · {stop(nm)[0]}", stop(nm)[1], f"={r05(ph_first + PH_NAMES.index(nm),'C')}", f"={r05(ph_first + PH_NAMES.index(nm),'D')}") for nm in PH_NAMES]

def java_rows():
    return [(f"Indonesia · {nm_}", dates, f"={r05(JAVA_ROWS[i],'C')}", f"={r05(JAVA_ROWS[i],'D')}") for i, (nm_, dates, _, _) in enumerate([stop(nm) for nm in JAVA_NAMES])]

def balig_rows():
    return [(f"Indonesia · {nm_}", dates, f"={r05(BALIG_ROWS[i],'C')}", f"={r05(BALIG_ROWS[i],'D')}") for i, (nm_, dates, _, _) in enumerate([stop(nm) for nm in BALIG_NAMES])]

def bali_proper_rows():
    idx = [BALIG_NAMES.index(nm) for nm in BALI_PROPER_NAMES]
    return [(f"Indonesia · {nm_}", dates, f"={r05(BALIG_ROWS[i],'C')}", f"={r05(BALIG_ROWS[i],'D')}") for i, (nm_, dates, _, _) in zip(idx, [stop(nm) for nm in BALI_PROPER_NAMES])]

def half_ph_rows():
    return [(f"Philippines · {nm_}", dates, f"={r05(ph_first + PH_NAMES.index(nm_),'C')}", f"={r05(ph_first + PH_NAMES.index(nm_),'D')}") for nm_, dates, _, _ in [stop(nm) for nm in PH_HALF_NAMES]]

def id_all_rows():
    out = []
    for i, nm in enumerate(ID_NAMES):
        nm_, dates, _, _ = stop(nm)
        out.append((f"Indonesia · {nm_}", dates, f"={r05(id_first + i,'C')}", f"={r05(id_first + i,'D')}"))
    return out

def au_row(dates):
    return ('AUSTRALIA · Lennox Head NSW — with auntie (free)', dates, '=HOST_N', '=AU_LIVE')

SCEN = []

# ---- S1
SCEN.append(build_scenario(
    'S1', 'THAILAND → AUSTRALIA (skip PH & Indonesia entirely)',
    'YES', 'Locked VN (28 Dec–22 Jan) · TH (22 Jan–12 Feb) · 12/13 Feb you fly Phuket→Brisbane, stay with auntie in Lennox Head to ~27 Feb · fly home. The lads carry on to Manila without you. Permanent exit to Australia = your one allowed solo.',
    route_rows=LOCKED_ROWS + [
        ('HKT ✈ BNE — you fly away, permanently', '12 Feb', '—', None),
        au_row('13 – 27 Feb'),
    ],
    cost_lines=LOCKED_COST,
    flight_lines=[('HKT → BNE (1 stop) — away from the group, for good', '=FLIGHT_HKT_BNE')],
    gap_lines=[],
    au_text='13–27 Feb',
    notes=[
        'You skip the two estimated chapters entirely: the Philippines (£1,253) and Indonesia (£1,189). Nothing is "saved" for later — the boys do them without you.',
        'This is the cheapest way to keep BOTH your non-negotiables: the SE Asia trip AND Australia. 46 Asia nights + 14 Australia nights = 60.',
        'Australia: auntie hosts you (free accom + food). eVisitor 651 = free for UK passports (90-day stay, plenty for 14 nights hosted).',
        'Return BNE→Gatwick/Heathrow, 1 stop — idealo saw £836 (01 Feb 2027); Virgin Australia quoted AUD 1,934–2,275 for Mar/Apr 2027. RE-CHECK WEEKLY FROM DECEMBER — this single fare decides whether S1 is "just about funded" or "needs the overdraft".',
        'You’d land back in the UK around 27 Feb 2027 — months earlier than the group. Different trip, honestly badged.',
    ]))

# ---- S2
SCEN.append(build_scenario(
    'S2', 'HALF PHILIPPINES → AUSTRALIA (Manila · El Nido · Coron)',
    'YES', 'Locked VN · TH · PH half with the lads (Manila 13 Feb · El Nido · Coron, through 23 Feb) · you fly away 23 Feb USU→MNL→BNE · auntie 23 Feb–9 Mar · home 9 Mar. 56 Asia nights + 14 = 70.',
    route_rows=LOCKED_ROWS + half_ph_rows() + [
        ('Coron USU ✈ MNL ✈ BNE — fly away from the group', '23 Feb', '—', None),
        au_row('23 Feb – 9 Mar'),
    ],
    cost_lines=LOCKED_COST + [('Philippines HALF — Manila (arrival) · El Nido · Coron', '=PHH_ALLIN')],
    flight_lines=[('USU → MNL (hop back to Manila)', '=FLIGHT_USU_MNL'), ('MNL → BNE (1 stop)', '=FLIGHT_MNL_BNE')],
    gap_lines=[],
    au_text='23 Feb–9 Mar',
    notes=[
        'This is your "half a Philippines" ask, done legal: the first 10 nights of the lads’ PH leg (Ola! Hostel Manila → Happiness Hostel El Nido → Coron), then you’re gone before Siargao.',
        'What you skip vs full PH: Siargao (5n, £234), Moalboal (3n, £103) and the Manila buffer night (£31) — saves ~£368 ground + the IAO→CEB→MNL backtrack (~£57).',
        'Flight path: USU→MNL on PAL from PHP 4,160 all-in (~£57) or Skyscanner US$65 — then MNL→BNE 1 stop (~£190; March is cheapest per KAYAK).',
        'El Nido (Tour A + lagoons) and Coron (Ultimate wreck tour) are the two best islands in the Philippines — you keep both. Siargao surf and Pescador sardine run go without you.',
        'Verdict territory: optimistic hours + max overdraft, or realistic + OD. See tab 07 — this is the realistic ceiling of your money.',
    ]))

# ---- S3
SCEN.append(build_scenario(
    'S3', 'FULL PHILIPPINES → AUSTRALIA (stay the whole PH leg)',
    'YES', 'Locked VN · TH · ALL 19 PH nights with the lads (Manila · El Nido · Coron · Siargao · Moalboal · buffer) · fly MNL→BNE 4 Mar · auntie 4–18 Mar · home 18 Mar. 65+14 = 79 nights.',
    route_rows=LOCKED_ROWS + ph_rows() + [
        ('MNL ✈ BNE — fly away from the group', '04 Mar', '—', None),
        au_row('04 – 18 Mar'),
    ],
    cost_lines=LOCKED_COST + [('Philippines FULL — 19 nights', '=PH_ALLIN')],
    flight_lines=[('MNL → BNE (1 stop)', '=FLIGHT_MNL_BNE')],
    gap_lines=[],
    au_text='04–18 Mar',
    notes=[
        'Everything the lads see in the Philippines, you see: Siargao (Sugba lagoon + surf), Moalboal (Pescador sardines + Kawasan canyoneering), plus El Nido and Coron.',
        'Extra vs S2 ≈ £503 of ground spend (Siargao £234 + Moalboal £103 + Manila buffer £31 + extra transport legs).',
        'If December hours stay at 21–25/wk, this one breaks you. It only pencils if December genuinely delivers 35 h/wk AND you use the full overdraft — and even then you’re near zero.',
        'MNL→BNE: March is KAYAK’s cheapest month ($686 RT / ~$343 one-way) but book 6–8 weeks ahead — it’s a thin route.',
    ]))

# ---- S4
SCEN.append(build_scenario(
    'S4', 'INDONESIA ONLY, SKIP PHILIPPINES → AUSTRALIA',
    'NO', 'Locked VN · TH · 13 Feb–4 Mar: you cannot be with the lads (Philippines) and flying home is banned — so 19 forced SOLO nights (priced) · then HKT→CGK to meet them Jakarta 4 Mar · FULL Indonesia · DPS→BNE 30 Mar. Breaks your no-solo rule.',
    route_rows=LOCKED_ROWS + [
        ('SOLO GAP — 19 nights alone (banned)', '13 Feb – 4 Mar', 19, None),
    ] + id_all_rows() + [
        ('DPS ✈ BNE — Australia after Indonesia', '30 Mar', '—', None),
        au_row('30 Mar – 13 Apr'),
    ],
    cost_lines=LOCKED_COST + [
        ('Indonesia from a Phuket departure (HKT→CGK replaces MNL→CGK)', ID_ALLIN_FROM_HKT),
    ],
    flight_lines=[('DPS → BNE (1 stop)', '=FLIGHT_DPS_BNE')],
    gap_lines=[('Solo gap — 19 nights @ £27.50/day (bed £8 + food £16 + rides £3.50)', '=19*(8+16+3.5)')],
    au_text='30 Mar–13 Apr',
    notes=[
        'NOT GROUP-LEGAL. The boys are in the Philippines 13 Feb–4 Mar. Being anywhere else in SE Asia alone is solo travel — your one hard rule. Being in London is banned by you too (and expensive).',
        'Costed anyway at £27.50/day × 19 ≈ £523, because you asked. It BUFFers with the ground spend.',
        'Even fully funded it costs MORE than S3 (HKT→CGK costs more than the MNL equivalent, and you eat 19 nights of solo spend).',
        'Legal equivalents that keep Indonesia: S8 (everything) or S7 (PH + Java only). Bali-only with the lads is S5/S6 — also not legal, same gap problem.',
        'If you simply cannot be with the lads in PH, your ONLY legal exits are S1 (12 Feb) or S2 (23 Feb).',
    ]))

# ---- S5
SCEN.append(build_scenario(
    'S5', 'BALI + GILIS ONLY (skip PH & Java) → AUSTRALIA',
    'NO', 'Locked VN · TH · 29 forced SOLO nights (13 Feb–14 Mar, pricing them) · fly HKT→DPS to meet the lads in Ubud 14 Mar · Bali + Gili Islands · DPS→BNE 30 Mar. Breaks your no-solo rule.',
    route_rows=LOCKED_ROWS + [
        ('SOLO GAP — 29 nights alone (banned)', '13 Feb – 14 Mar', 29, None),
    ] + balig_rows() + [
        ('DPS ✈ BNE — Australia', '30 Mar', '—', None),
        au_row('30 Mar – 13 Apr'),
    ],
    cost_lines=LOCKED_COST + [
        ('Bali + Gili Islands — Ubud · Gili T · Gili Air · Canggu · Uluwatu (meet lads 14 Mar)', '=BALIG_ALLIN'),
    ],
    flight_lines=[('HKT → DPS (direct, AirAsia)', '=FLIGHT_HKT_DPS'), ('DPS → BNE (1 stop)', '=FLIGHT_DPS_BNE')],
    gap_lines=[('Solo gap — 29 nights @ £27.50/day (13 Feb – 14 Mar)', '=29*(8+16+3.5)')],
    au_text='30 Mar–13 Apr',
    notes=[
        'NOT GROUP-LEGAL — same problem as S4 but bigger: 29 solo nights while the lads do all of PH + Java.',
        'If the gap were legal you’d do: HKT→DPS direct (AirAsia, ~£80, non-stop exists), then Ubud (Poshtel) 14–17 Mar · Gili T 17–20 · Gili Air 20–22 · Canggu (Tipsy Gypsy) 22–26 · Uluwatu (Nala’s) 26–30.',
        'Gilis party hard (Gili T nightlife £58 + £51 food) — it’s the same spend as S4 but the Bali beaches actually land.',
        'Cheapest “Indonesia” that still touches Bali — but illegal, and still unfundable. Dead end. Legal version of “Bali only” does not exist; closest is S8 minus the Java trains you fly past anyway.',
    ]))

# ---- S6
SCEN.append(build_scenario(
    'S6', '“JUST BALI” — Ubud · Canggu · Uluwatu (no Gilis) → AUSTRALIA',
    'NO', 'Locked VN · TH · 29 forced SOLO nights (13 Feb–14 Mar) · HKT→DPS to meet the lads Ubud 14 Mar · Bali proper only · DPS→BNE 30 Mar. Breaks your no-solo rule.',
    route_rows=LOCKED_ROWS + [
        ('SOLO GAP — 29 nights alone (banned)', '13 Feb – 14 Mar', 29, None),
    ] + bali_proper_rows() + [
        ('DPS ✈ BNE — Australia', '30 Mar', '—', None),
        au_row('30 Mar – 13 Apr'),
    ],
    cost_lines=LOCKED_COST + [
        ('Just Bali — Ubud · Canggu · Uluwatu · NO Gilis (meet lads 14 Mar)', '=BALI_ALLIN'),
    ],
    flight_lines=[('HKT → DPS (direct, AirAsia)', '=FLIGHT_HKT_DPS'), ('DPS → BNE (1 stop)', '=FLIGHT_DPS_BNE')],
    gap_lines=[('Solo gap — 29 nights @ £27.50/day (13 Feb – 14 Mar)', '=29*(8+16+3.5)')],
    au_text='30 Mar–13 Apr',
    notes=[
        'NOT GROUP-LEGAL — 29 solo nights. Costed because you asked “what about JUST Bali”.',
        'Bali proper: Poshtel Ubud 14–17 Mar · Tipsy Gypsy Canggu 22–26 Mar · Nala’s Home Uluwatu 26–30 Mar. You GIVE UP 12 nights of Gili Islands to save ~£309.',
        'This is the cheapest post-TH scenario on paper — but you still can’t legally/financially do it before Australia. Dead end under your rules.',
        'If your rule ever flexed for legal solo days (e.g. a confirmed Australia-first route), this is the shape to price.',
    ]))

# ---- S7
SCEN.append(build_scenario(
    'S7', 'FULL PHILIPPINES + JAVA — then fly away (skip Bali & Gilis)',
    'YES', 'Locked VN · TH · FULL PH (13 Feb–4 Mar) with the lads · FULL JAVA (04–14 Mar) · then you fly away Banyuwangi→SUB→BNE · auntie 14–28 Mar · home 28 Mar. 74+14 = 88 nights.',
    route_rows=LOCKED_ROWS + ph_rows() + java_rows() + [
        ('Banyuwangi → SUB ✈ BNE — fly away from the group', '14 Mar', '—', None),
        au_row('14 – 28 Mar'),
    ],
    cost_lines=LOCKED_COST + [
        ('Philippines FULL — 19 nights', '=PH_ALLIN'),
        ('Java — Jakarta · Yogyakarta · Malang · Bromo · Banyuwangi (meet lads after PH)', JAVA_ALLIN_MNL),
    ],
    flight_lines=[('Banyuwangi → Surabaya SUB (bus/train)', '=GND_BWG_SUB'), ('SUB → BNE via Singapore (AirAsia)', '=FLIGHT_SUB_BNE')],
    gap_lines=[],
    au_text='14–28 Mar',
    notes=[
        'GROUP-LEGAL: you ride the whole PH leg and the whole Java leg with them, then peel off in East Java. The boys continue: Ijen → Ubud → Gilis → Canggu → Uluwatu.',
        'Java leg: KAI Gajahwong overnight Jakarta→Yogyakarta (Prambanan + Borobudur day trips) · overnight train to Malang · Bromo crater dawn (255k IDR park fee) · Ijen blue fire.',
        'SUB→BNE via SIN ~£165 (no direct flight; AirAsia 1-stop 11h45). Banyuwangi→SUB is ~5–6h public transport (~£8).',
        'This is “everything except Bali” — the strongest trip you could nearly buy. Adds ~£414 to S3 for Borobudur + Bromo + Ijen.',
        'Funding: optimistic-hours + full overdraft and pray. If December under-delivers, collapse to S2.',
    ]))

# ---- S8
SCEN.append(build_scenario(
    'S8', 'THE FULL 90-DAY PLAN + AUSTRALIA (the lads’ trip, your exit)',
    'YES', 'Locked VN · TH · PH FULL · ID FULL — the friends’ exact 90-day itinerary · DPS→BNE 30 Mar · auntie 30 Mar–13 Apr · home 13 Apr. 90+14 = 104 nights.',
    route_rows=LOCKED_ROWS + ph_rows() + id_all_rows() + [
        ('DPS ✈ BNE — Australia after the full plan', '30 Mar', '—', None),
        au_row('30 Mar – 13 Apr'),
    ],
    cost_lines=LOCKED_COST + [
        ('Philippines FULL — 19 nights', '=PH_ALLIN'),
        ('Indonesia FULL — Java + Bali + Gilis', '=ID_ALLIN'),
    ],
    flight_lines=[('DPS → BNE (1 stop)', '=FLIGHT_DPS_BNE')],
    gap_lines=[],
    au_text='30 Mar–13 Apr',
    notes=[
        'The friends’ full-time plan exactly as scoped: 30 stops, 90 nights, 4 countries — with Australia bolted on the end and a BNE→Gatwick/Heathrow flight home.',
        'Sanity check vs your own workbook: ground total there £4,896.73 + 8% = £5,288.46; workbook all-in London £5,702.46 (DPS→LGW £414). Add Australia: + DPS→BNE £150 + BNE→LHR £840 − nothing else → the honest all-in is tab 07’s S8 number. Trust THIS sheet’s formulas over both old figures.',
        'Cheapest seat in the cabin for this route: sharing 6-bed private dorms with the lads (5 people), which the plan already assumes.',
        'LEGAL ✓ — but financially out of reach. See tab 10 for the numbers that make that true.',
    ]))

# ---- S9
SCEN.append(build_scenario(
    'S9', 'HALF PH + JAVA, then fly away (your exact example, costed)',
    'NO', 'Locked VN · TH · half PH with the lads (through Coron, 23 Feb) · then 8 SOLO nights alone in Manila (23 Feb–3 Mar — the lads are in Siargao/Moalboal) · rejoin them Java 04 Mar · Java with lads · fly away Banyuwangi 14 Mar · auntie 14–28 Mar. Breaks your no-solo rule.',
    route_rows=LOCKED_ROWS + half_ph_rows() + [
        ('SOLO GAP — 8 nights alone in Manila (banned)', '23 Feb – 3 Mar', 8, None),
    ] + java_rows() + [
        ('Banyuwangi → SUB ✈ BNE — fly away', '14 Mar', '—', None),
        au_row('14 – 28 Mar'),
    ],
    cost_lines=LOCKED_COST + [
        ('Philippines HALF — Manila · El Nido · Coron (with lads)', '=PHH_ALLIN'),
        ('Java — Jakarta→Banyuwangi (with lads from 04 Mar)', JAVA_ALLIN_MNL),
    ],
    flight_lines=[('Banyuwangi → Surabaya SUB (bus/train)', '=GND_BWG_SUB'), ('SUB → BNE via Singapore (AirAsia)', '=FLIGHT_SUB_BNE')],
    gap_lines=[('Solo gap — 8 nights Manila buffer @ £25.98/day (bed £6.98 + food £16 + rides £3)', '=8*(6.98+16+3)')],
    au_text='14–28 Mar',
    notes=[
        'NOT GROUP-LEGAL: you’d be alone in Manila 23 Feb–3 Mar while the lads do Siargao + Moalboal. Your rule says no — Australia is the only solo permitted.',
        'This is “half a Philippines, Java, and then fly away from my friends” priced honestly: half PH + Java + the 8 solo nights you tried to skip.',
        'Legal equivalents of the same instinct: S2 (drop PH at Coron → Australia — cheapest) or S7 (full PH + Java → fly away — the lawful version of exactly this).',
        'The gap alone costs £208 + you lose the cheapest beds in the cabin (the lads’ Siargao/Moalboal nights are hostel-twin-share).',
        'If the lads’ PH leg were ever halved for everyone (not just you), this legalises — but that is their call, not yours.',
    ]))

# ================= 07 SCENARIO SUMMARY =================
ws = sheet(wb, '07 SCENARIO SUMMARY', ORANGE)
NC = 17
title(ws, 1, 1, NC, '07 · SCENARIO SUMMARY — WHAT YOUR MONEY ACTUALLY BUYS',
      'All scenarios include: locked VN+TH (28 Dec–12 Feb) + Australia (2 weeks hosted, free) + a BNE→Gatwick/Heathrow return flight. Buffer 8% on ground only. Live formulas — change 01/06 and this re-ranks itself.')
band(ws, 4, 1, NC, 'YOUR FOUR ENVELOPES (from tab 04) — the measuring stick')
ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=4)
C(ws, 5, 1, 'Envelope', bold=True, size=8.5, color='FFFFFF', fill=STEEL, align='left')
C(ws, 5, 5, '£ realistic', bold=True, size=8.5, color='FFFFFF', fill=STEEL, align='center')
C(ws, 5, 6, '£ optimistic', bold=True, size=8.5, color='FFFFFF', fill=STEEL, align='center')
ws.row_dimensions[5].height = 16
env_rows_07 = [
    ('A / B — NO overdraft (the honest plan)', '=ENV_A', '=ENV_B'),
    ('C / D — MAX £1,000 interest-free overdraft (your ceiling)', '=ENV_C', '=ENV_D'),
    ('E / F — worst case: birthday & Christmas never land (no OD)', '=ENV_E', '=ENV_F'),
    ('worst case + max OD', '=ENV_E+OD', '=ENV_F+OD'),
]
r = 6
for label, a, b in env_rows_07:
    merge_lab(ws, r, 1, 4, label, size=9)
    money(ws, r, 5, a, bold=True, fill=CREAM); money(ws, r, 6, b, bold=True, fill=CREAM)
    r += 1
ENV_TBL_END = r - 1

r += 1
band(ws, r, 1, NC, 'SCENARIO COMPARISON — nine ways to spend the same money')
HDR_R = r + 1
headers = [(1,'No'),(2,'Scenario'),(3,'Group-legal?'),(4,'Exit point'),(5,'Asia n'),(6,'AU n'),(7,'Total n'),
           (8,'Ground + gap'),(9,'8% buffer'),(10,'Asia→AU flights'),(11,'AU return'),(12,'SCENARIO TOTAL'),
           (13,'vs A (real·no OD)'),(14,'vs B (opt·no OD)'),(15,'vs C (real·max OD)'),(16,'vs D (opt·max OD)'),(17,'Verdict')]
hdr(ws, HDR_R, headers, height=26)
SCEN_META = [
    ('S1', 'VN+TH only → Australia (12/13 Feb)', 'YES ✓', 'HKT · 12 Feb'),
    ('S2', 'VN+TH + HALF PH → Australia (23 Feb)', 'YES ✓', 'USU · 23 Feb'),
    ('S3', 'VN+TH + FULL PH → Australia (04 Mar)', 'YES ✓', 'MNL · 04 Mar'),
    ('S4', 'Indonesia only, skip PH (ILLEGAL solo gap)', 'NO ✗', 'DPS · 30 Mar'),
    ('S5', 'Bali + Gilis only, skip PH & Java (ILLEGAL)', 'NO ✗', 'DPS · 30 Mar'),
    ('S6', 'JUST BALI — no Gilis (ILLEGAL)', 'NO ✗', 'DPS · 30 Mar'),
    ('S7', 'VN+TH + FULL PH + JAVA → Australia (14 Mar)', 'YES ✓', 'SUB · 14 Mar'),
    ('S8', 'FULL 90-DAY PLAN + AUSTRALIA (30 Mar)', 'YES ✓', 'DPS · 30 Mar'),
    ('S9', 'Half PH + JAVA → Australia (ILLEGAL 8-night gap)', 'NO ✗', 'SUB · 14 Mar'),
]
FIRST_SCEN_ROW = HDR_R + 1
r = FIRST_SCEN_ROW
for i, ((code, nm, legal, exitpt), ref) in enumerate(zip(SCEN_META, SCEN)):
    row_fill = CREAM if i % 2 else None
    C(ws, r, 1, code, bold=True, align='center', fill=row_fill)
    C(ws, r, 2, nm, size=8.5, fill=row_fill, wrap=True)
    C(ws, r, 3, legal, bold=True, align='center', size=9,
      color='1F7A33' if legal.startswith('YES') else 'B23B3B', fill=row_fill)
    C(ws, r, 4, exitpt, size=8.5, align='center', fill=row_fill)
    C(ws, r, 5, f"='{code}'!C{ref['route_tot']}-HOST_N", fmt=INT, align='center', fill=row_fill)
    C(ws, r, 6, '=HOST_N', fmt=INT, align='center', fill=row_fill)
    C(ws, r, 7, f"='{code}'!C{ref['route_tot']}", fmt=INT, align='center', fill=row_fill)
    money(ws, r, 8, f"='{code}'!D{ref['ground_sub']}", fill=row_fill)
    money(ws, r, 9, f"='{code}'!D{ref['buffer']}", fill=row_fill)
    money(ws, r, 10, f"=L{r}-H{r}*(1+BUF)-K{r}", fill=row_fill)
    money(ws, r, 11, '=FLIGHT_BNE_LHR', fill=row_fill)
    money(ws, r, 12, f"='{code}'!D{ref['total']}", bold=True, fill=LBLUE, fmt=GBP)
    money(ws, r, 13, f"=ENV_A-L{r}", fmt='£#,##0.00;[Red]-£#,##0.00', fill=row_fill)
    money(ws, r, 14, f"=ENV_B-L{r}", fmt='£#,##0.00;[Red]-£#,##0.00', fill=row_fill)
    money(ws, r, 15, f"=ENV_C-L{r}", fmt='£#,##0.00;[Red]-£#,##0.00', fill=row_fill)
    money(ws, r, 16, f"=ENV_D-L{r}", fmt='£#,##0.00;[Red]-£#,##0.00', fill=row_fill)
    C(ws, r, 17, f'=IF(L{r}<=ENV_A,"Funded (real, no OD)",IF(L{r}<=ENV_B,"Funded (opt, no OD)",IF(L{r}<=ENV_C,"Tight · FULL £1,000 OD",IF(L{r}<=ENV_D,"Barely · opt + max OD","NOT FUNDED"))))',
      size=8, align='center', fill=row_fill, wrap=True)
    ws.row_dimensions[r].height = 26
    r += 1
LAST_SCEN_ROW = r - 1
note(ws, r, 1, NC, 'Asia→AU flights cell is derived (TOTAL − ground×1.08 − return). Negative = the scenario is cheaper than the return flight alone would suggest — never happens here, but the formula stays honest if you edit tab 06. Ground+gap INCLUDES the 8% buffer; flights never get one — deliberate, matching your workbook.', height=16)

chart = BarChart()
chart.type = 'col'
chart.style = 10
chart.y_axis.title = '£ per person'
chart.x_axis.title = 'Scenario'
chart.y_axis.numFmt = '£#,##0'
chart.title = 'SCENARIO TOTAL vs OPTIMISTIC + MAX OVERDRAFT (your absolute ceiling)'
from openpyxl.chart import Series
CATS = Reference(ws, min_col=2, min_row=FIRST_SCEN_ROW, max_row=LAST_SCEN_ROW)
s1 = Series(Reference(ws, min_col=12, min_row=FIRST_SCEN_ROW, max_row=LAST_SCEN_ROW), title='SCENARIO TOTAL')
# hidden helper column R repeats ENV_D per row (keeps chart honest without cluttering the sheet)
helper_col = 18
C(ws, HDR_R, helper_col, 'ENV D ceiling', bold=True, size=8, color='FFFFFF', fill=STEEL, align='center')
for rr in range(FIRST_SCEN_ROW, LAST_SCEN_ROW + 1):
    money(ws, rr, helper_col, '=ENV_D', fmt=GBP)
s2 = Series(Reference(ws, min_col=helper_col, min_row=FIRST_SCEN_ROW, max_row=LAST_SCEN_ROW), title='OPTIMISTIC + FULL £1,000 OVERDRAFT (absolute ceiling)')
chart.append(s1)
chart.append(s2)
from openpyxl.chart.data_source import AxDataSource, StrRef
_cat = AxDataSource(strRef=StrRef(f"'07 SCENARIO SUMMARY'!$B${FIRST_SCEN_ROW}:$B${LAST_SCEN_ROW}"))
for _s in chart.series:
    _s.cat = _cat
chart.height = 11
chart.width = 22
chart.gapWidth = 60
chart.visible_cells_only = False
chart.display_blanks = 'gap'
chart.legend.position = 'b'
ws.add_chart(chart, f'A{LAST_SCEN_ROW + 2}')
ws.column_dimensions['R'].hidden = True
footer(ws, LAST_SCEN_ROW + 26, NC)
widths(ws, {'A': 6, 'B': 38, 'C': 13, 'D': 13, 'E': 12, 'F': 12, 'G': 9, 'H': 15, 'I': 13, 'J': 15, 'K': 13, 'L': 17,
            'M': 15, 'N': 15, 'O': 15, 'P': 15, 'Q': 24, 'R': 13})

# ================= 10 AS IT IS (VERDICT) =================
ws = sheet(wb, '10 AS IT IS (VERDICT)', 'B23B3B')
NC = 8
title(ws, 1, 1, NC, '10 · AS IT IS — THE HONEST VERDICT',
      'No sugar-coating. Every number is live (trace it on tabs 02–07). Read this before you book anything.')
verdict_lines = [
    ('1', '="The brutal, exact ceiling: you end 27 Dec with "&TEXT(ENV_A,"£#,##0")&" realistic / "&TEXT(ENV_B,"£#,##0")&" optimistic BEFORE the overdraft — "&TEXT(ENV_C,"£#,##0")&" / "&TEXT(ENV_D,"£#,##0")&" with it. Birthday and Christmas are hopes; without them: "&TEXT(ENV_E,"£#,##0")&" / "&TEXT(ENV_F,"£#,##0")&"."'),
    ('2', '="The locked Vietnam + Thailand leg costs "&TEXT(VNTH_ALLIN,"£#,##0.00")&" (46 nights). The Philippines (est. £1,253) and Indonesia (est. £1,189) each cost more than your ENTIRE free cash flow after Phuket — full stop."'),
    ('3', "=\"S1 — fly Phuket→Brisbane straight after Thailand (12/13 Feb, £195) — the ONLY scenario fundable with realistic hours and NO overdraft… and even then only just: \"&TEXT('07 SCENARIO SUMMARY'!$L$13,\"£#,##0\")&\" total vs \"&TEXT(ENV_B,\"£#,##0\")&\" optimistic-no-OD. Realistic-no-OD gap: \"&TEXT(ENV_A-'07 SCENARIO SUMMARY'!$L$13,\"£#,##0\")&\".\""),
    ('4', "=\"S2 — the half-Philippines you asked for — is the honest ceiling: \"&TEXT('07 SCENARIO SUMMARY'!$L$14,\"£#,##0\")&\" all-in. It NEEDS the full interest-free overdraft: realistic+OD \"&TEXT(ENV_C,\"£#,##0\")&\" covers by \"&TEXT(ENV_C-'07 SCENARIO SUMMARY'!$L$14,\"£#,##0\")&\". Optimistic-no-OD \"&TEXT(ENV_B,\"£#,##0\")&\" does NOT cover it (short \"&TEXT('07 SCENARIO SUMMARY'!$L$14-ENV_B,\"£#,##0\")&\"). Optimistic+OD covers by \"&TEXT(ENV_D-'07 SCENARIO SUMMARY'!$L$14,\"£#,##0\")&\".\""),
    ('5', "=\"S3 — full Philippines — totals \"&TEXT('07 SCENARIO SUMMARY'!$L$15,\"£#,##0\")&\". Optimistic hours AND the full overdraft with \"&TEXT(ENV_D-'07 SCENARIO SUMMARY'!$L$15,\"£#,##0\")&\" to spare. One fat price rise on BNE→LHR (idealo saw £836; Virgin Australia wants AUD 2,275 ≈ £1,112 in March) breaks it. Treat S3 as NOT FUNDED.\""),
    ('6', 'S4, S5, S6 — skipping PH and/or Java and “meeting the boys later” — all contain 19–29 SOLO NIGHTS, which your own rule forbids. They are also more expensive than S3. They are dead options, not budget options.'),
    ('7', "=\"S7 — full PH + Java, fly away 14 Mar — \"&TEXT('07 SCENARIO SUMMARY'!$L$19,\"£#,##0\")&\". S9 — your exact example (half PH + Java) — \"&TEXT('07 SCENARIO SUMMARY'!$L$21,\"£#,##0\")&\" including 8 banned solo nights in Manila. Both exceed optimistic+max-OD. Both out of reach.\""),
    ('8', "=\"S8 — the lads’ 90-day plan + Australia + a BNE→Gatwick fare home — \"&TEXT('07 SCENARIO SUMMARY'!$L$20,\"£#,##0\")&\". You are \"&TEXT('07 SCENARIO SUMMARY'!$L$20-ENV_D,\"£#,##0\")&\" short of your absolute ceiling (optimistic hours + full overdraft, \"&TEXT(ENV_D,\"£#,##0\")&\"). That is not a budget problem. That is a different job, a different year, or richer relatives.\""),
    ('9', 'AUSTRALIA MINIMUM TICKET: exit fare (£195 from Phuket, 13 Feb — cheapest) + BNE→LHR return (£840) = £1,035 before a single night out. Your auntie kills the visa-living-cost problem (651 = free), nothing else. Australia is affordable ONLY in the cheap-exit form (S1/S2/S3 shape).'),
    ('10', 'THE SWING FACTORS, ranked: (1) BNE→LHR price — hunt it Dec–Jan, it moves £200+/month; (2) December hours — 21→35 h/wk is +£754 net, bigger than any fare saving; (3) birthday/Christmas actually landing (±£400); (4) pension auto-enrolment — opt OUT if you can, ~£50–89 of net pay; (5) tax — £0 expected, but only while cumulative income stays under £12,570 (headroom ≈ £8,300).'),
    ('11', 'TAX & NI, for the record: NI ≈ £49 total on your Oct–Dec bar pay (weekly PT £242, 8%). Income tax £0. No student loan below £25k. You are not being taxed out of the trip — your hours are.'),
    ('12', 'DO NOT buy anything yet: (a) confirm December roster ≥ 30 h/wk; (b) re-price BNE→LHR + HKT→BNE weekly from 1 Dec; (c) book eVisitor 651 (free, 10 min) two weeks before flying; (d) tell the lads by end of November that you’re capping at S2 (or S1).'),
    ('13', 'IF DECEMBER DELIVERS: 38.5 h weeks like period 32 every week → +£754 net → S3 becomes real (with OD), S7 starts whispering. IF IT DOESN’T: drop to S1 without shame — Australia + locked Asia is still a life-changing trip.'),
    ('14', 'ONE LEGAL LOOPHOLE, not yours to pull alone: if the GROUP halves the Philippines for everyone, S2-class economics apply to all five of you and nobody is solo. Talk to the lads — the plan is theirs as much as yours.'),
    ('15', "=\"BOTTOM LINE: without the overdraft you cannot do Australia and anything beyond Thailand. With it, you can do half a Philippines. The full itinerary plus Australia is \"&TEXT('07 SCENARIO SUMMARY'!$L$20-ENV_D,\"£#,##0\")&\" beyond your absolute ceiling. Everything in this file is built so you can watch that truth move as December lands.\""),
]
r = 4
for n_, text in verdict_lines:
    C(ws, r, 1, n_, bold=True, size=12, color='FFFFFF', fill='B23B3B', align='center')
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=NC)
    C(ws, r, 2, text, size=9.5, wrap=True, border=None, align='left')
    ws.row_dimensions[r].height = 44
    r += 1
footer(ws, r + 1, NC)
widths(ws, {'A': 5, 'B': 30, 'C': 30, 'D': 30, 'E': 30, 'F': 30, 'G': 30, 'H': 30})

# ================= 11 Sources & Method =================
ws = sheet(wb, '11 Sources & Method', STEEL)
NC = 6
title(ws, 1, 1, NC, '11 · SOURCES & METHOD', 'Everything in this workbook traced · dates = when facts were checked · GBP throughout · not financial advice — an estimate engine, not a promise.')
band(ws, 4, 1, NC, 'A · YOUR DATA (all supplied by you)')
r = 5
for txt in [
    'Payslips periods 28–34 (Oct–Nov 2026): 179 h, £2,275.09 gross at £12.71/h — bar job started Oct 2026; aiming for full-time hours.',
    'Balance £1,016.26 · savings £247 · birthday ~£200 (estimate) · Christmas ~£200 (estimate) · £1,000 interest-free student overdraft · £150 other job.',
    'Fixed: £135/month rent+phone+gym — taken LITERALLY as a combined total. If that £135 is actually rent-only-ish, envelopes move.',
    'Pre-trip buy list: insurance £200 · shoes £50. Home food costs you £0.',
    'Departure 27 Dec 2026 one-way LGW→Hanoi (booked, excluded from budgets). Australia leg: you fly home Gatwick/Heathrow after auntie’s.',
    'Trip framework: 5 × 24-y-o males · VN+TH locked (14 stops, published Hostelworld/Booking prices) · PH/ID = your workbook’s ESTIMATED placeholders · Australia = auntie Michelle hosts 1–2 weeks (living £0) + you only pay flights.',
]:
    merge_lab(ws, r, 1, NC, '• ' + txt, size=9, color='26221C', wrap=True)
    ws.row_dimensions[r].height = 26
    r += 1
r += 1
band(ws, r, 1, NC, 'B · TAX & NATIONAL INSURANCE (2026/27, gov.uk rates & thresholds — confirmed Nov 2026)')
r += 1
for txt in [
    'Class 1 employee NI (category A): 0% up to PT £242/wk · 8% £242–£967 (UEL) · 2% above £967/wk. Your £325 typical week loses ~£6.64 to NI; your £489 period-32 week lost ~£19.79.',
    '2026/27 NI thresholds: LEL £129/wk · PT £242/wk · UEL £967/wk — employee rate unchanged at 8% (gov.uk “Rates and thresholds for employers 2026 to 2027”).',
    'Income tax (rUK): personal allowance £12,570 (frozen to Apr 2028) · basic rate 20% · higher 40% above £50,270. Cumulative Oct–Dec bar gross ≈ £3.90–4.15k + £2,000 prior estimate = still £8k+ clear of PA → £0 tax expected.',
    'If prior earnings Apr–Sep actually exceed ~£8,400, each extra £1,000 costs £200 (20%). Update PRIOR_EARN on tab 01 — the tax check on tab 03 recomputes.',
    'Student loan: nothing deducted under plan thresholds (~£25k+). Pension: workplace auto-enrolment NOT modelled — opt out or lose ~3–5% net; ask your employer.',
    'Scotland would pay different (starter/intermediate) rates — assumed England/Wales.',
]:
    merge_lab(ws, r, 1, NC, '• ' + txt, size=9, color='26221C', wrap=True)
    ws.row_dimensions[r].height = 26
    r += 1
r += 1
band(ws, r, 1, NC, 'C · FLIGHTS RESEARCHED 16 Nov 2026 (book by late Dec / early Jan; prices WILL move)')
r += 1
for txt in [
    'LGW→Hanoi — booked (excluded). HCMC→BKK £60 (Vietjet direct, dated 22 Jan card). HKT→MNL £137 (Vietjet 1-stop, dated card). All inside the locked £2,454.92.',
    'USU→MNL £60 (PAL PHP 4,160 all-in · Skyscanner US$65 · Kayak $75 · eDreams ~$110 avg) · MNL→BNE £190 (Skyscanner $198 lowest seen · PAL $334 · KAYAK $346; March cheapest month, $686 RT).',
    'HKT→CGK £95 (Skyscanner $111–131 · Traveloka $111) · HKT→DPS £80 (Skyscanner $81 · KAYAK $92 · AirAsia non-stop exists) · HKT→BNE £195 (Expedia $266 · Skyscanner $235 · Trip.com $234 OW).',
    'SUB→BNE £165 (Skyscanner $217 via SIN · Trip.com $184 · AirAsia 1-stop SIN 11h45) · DPS→BNE £150 (Expedia $165 · BatikAir direct $184 — direct exists BNE–DPS).',
    'BNE→LHR £840 — idealo routes BNE–LHR “from £836” (01 Feb 2027) · Skyscanner lowest-seen $378 · Virgin Australia: Dec-26 AUD 3,252 · Mar-27 AUD 2,275 · Apr-27 AUD 1,934 (≈ £1,080/£1,112/£950) · Cathay AUD 2,057 (~£1,010) · idealo £836 treated as central.',
    'DPS→LON £414 (your workbook, 1 stop 18h35) — cheaper but ILLEGAL by your rules (skips Australia). Listed only so nobody “saves” it later by accident.',
    'AUD→GBP ≈ 0.49 · USD→GBP ≈ 0.78 · THB→GBP ≈ 0.021 · PHP→GBP ≈ 0.0135 · IDR≈0.000048 (workbook) · fares one-way economy, no bags unless stated.',
]:
    merge_lab(ws, r, 1, NC, '• ' + txt, size=9, color='26221C', wrap=True)
    ws.row_dimensions[r].height = 22
    r += 1
r += 1
band(ws, r, 1, NC, 'D · METHOD — how the numbers were built')
r += 1
for txt in [
    'Locked legs: VN+TH stops (Hostelworld/Booking published prices, your workbook checked 13 Nov 2026) + confirmed leg prices (12Go dated quotes + dated Google Flights cards) = £2,454.92 all-in ground for 46 nights.',
    'PH/ID: your workbook’s ESTIMATES (hostel twin-share for 5 × 24-y-o males; e.g. El Nido £68 accommodation, Siargao £58, Canggu £22.60) — unverified, treat as ±15%.',
    '8% contingency buffer on GROUND spend only (not flights) — same rule as your workbook (£391.74 was 8% of £4,896.73).',
    'Solo-gap nights priced at £27.50/day (bed £8 + food £16 + rides £3.50) — deliberately hostel-floor pricing; real cost higher.',
    'Australia: auntie hosts → accom+food £0, nights = HOST_N (14 default, editable). Return flight BNE→Gatwick/Heathrow 1 stop. eVisitor 651 (free) assumed; Working Holiday 417 (~£345) only if you later decide to WORK — flag it then.',
    'Scenario totals = ground × 1.08 + Asia→AU flights + BNE→LHR + Australia living (£0). No double counting: balance £1,016.26 already holds Oct wages; outstanding 33–34 added net; w/c 21 Dec included per your instruction.',
    'Rounding: £ shown to 2dp; totals formula-driven; transport legs may differ ±2p from your CSV due to source rounding (£796.61 vs £796.63).',
]:
    merge_lab(ws, r, 1, NC, '• ' + txt, size=9, color='26221C', wrap=True)
    ws.row_dimensions[r].height = 22
    r += 1
r += 1
band(ws, r, 1, NC, 'E · WHAT TO CHANGE WHEN REALITY LANDS (in priority order)')
r += 1
for txt in [
    '1. December roster lands → update OPT_HRS (or REAL_HRS if it settles lower) on tab 01 — every envelope and verdict re-ranks instantly.',
    '2. Every 2 weeks: re-price HKT→BNE (if S1/S2) or DPS→BNE (S4+) and BNE→LHR on tab 06; if BNE→LHR passes £900, re-read tab 10 line 13 before committing to anything.',
    '3. Birthday money actually lands → nothing to change (it’s already counted); if it DOESN’T, read the worst-case envelopes on tab 04/07 (E/F).',
    '4. Auntie offers different dates / longer stay → HOST_N on tab 01 (14 → 7/21 nights changes nothing financially except your sanity).',
    '5. You decide to WORK in Australia → you need the 417 visa (~£345) + real living costs — re-cost from scratch; this workbook says hosted-visit only.',
    '6. Payslips for w/c 23 Nov & 30 Nov land → gift-check the £3.50 travel and the 25.57 h average — if it’s 28+ hours, tab 04 gets happier on its own.',
]:
    merge_lab(ws, r, 1, NC, txt, size=9, color='26221C', wrap=True)
    ws.row_dimensions[r].height = 18
    r += 1
r += 1
band(ws, r, 1, NC, 'F · DISCLAIMER')
C(ws, r + 1, 1, 'Flight prices, visa fees and tax thresholds move. This workbook is an estimate engine for decisions taken Nov 2026–Jan 2027. It is not regulated financial advice. If figures disagree with your bank, the bank wins. Built 16 Nov 2026 from your supplied data + public research (gov.uk, Skyscanner, Expedia, KAYAK, idealo, Virgin Australia, Cathay Pacific, Philippine Airlines, AirAsia, Home Affairs Australia, 12Go, Hostelworld, Booking.com).', size=8, italic=True, color='6B6255', border=None, align='left', wrap=True)
ws.row_dimensions[r + 1].height = 40
footer(ws, r + 3, NC)
widths(ws, {'A': 60, 'B': 40, 'C': 40, 'D': 40, 'E': 40, 'F': 40})

# ================= 00 READ ME =================
ws = sheet(wb, '00 READ ME', NAVY)
NC = 7
title(ws, 1, 1, NC, 'SEA 2027 · BUDGET vs AUSTRALIA',
      'Your Vietnam+Thailand → ??? → Australia problem, priced to the penny · built 16 Nov 2026 from your payslips, workbook & fresh fare research · GBP per person')
note(ws, 4, 1, NC, 'What this answers in one line: after locking Vietnam + Thailand (£2,454.92) and before the non-negotiable Australia leg + BNE→Gatwick/Heathrow flight, YOUR £1,016 + wages buys you Vietnam + Thailand + half a Philippines if you max the interest-free overdraft — and Vietnam + Thailand + Australia only if December plays along.',
     size=9, color='16324F', fill=LBLUE, height=44)
band(ws, 6, 1, NC, 'THE THREE RULES BAKED IN (tell me if I’ve got these wrong)')
ws2 = wb['00 READ ME']
r = 7
for txt in [
    '1. AUSTRALIA IS 100% HAPPENING — every scenario includes Australia (2 weeks hosted by auntie Michelle, Lennox Head NSW, living £0) and a BNE→Gatwick/Heathrow return flight (~£840).',
    '2. VIETNAM + THAILAND ARE LOCKED — £2,454.92 all-in (46 nights), priced from your own workbook (checked 13 Nov 2026). Included, untouched, in EVERY scenario.',
    '3. NEVER SOLO — Australia is the only permitted solo leg. Scenarios that strand you alone in Asia (S4, S5, S6, S9) are flagged red — still costed because you asked.',
]:
    merge_lab(ws2, r, 1, NC, txt, size=9, color='26221C', wrap=True)
    ws2.row_dimensions[r].height = 19
    r += 1
r += 1
band(ws2, r, 1, NC, 'HEADLINE NUMBERS (live — tabs 04 & 07)')
r += 1
headlines = [
    ('Locked Vietnam + Thailand (46 nights)', '=VNTH_ALLIN', GBP),
    ('Cheapest Australia route: exit Phuket 12/13 Feb + return (S1)', "='S1'!D" + str(next(s['total'] for s in SCEN if s['code'] == 'S1')), GBP),
    ('Envelope — realistic hours, no overdraft (A)', '=ENV_A', GBP),
    ('Envelope — optimistic hours, no overdraft (B)', '=ENV_B', GBP),
    ('Envelope — max interest-free overdraft, optimistic (D)', '=ENV_D', GBP),
    ('THE FULL 90-DAY PLAN + AUSTRALIA (S8)', "='S8'!D" + str(next(s['total'] for s in SCEN if s['code'] == 'S8')), GBP),
]
for label, formula, fmt in headlines:
    merge_lab(ws2, r, 1, 5, label, size=9.5)
    money(ws2, r, 6, formula, bold=True, fill=CREAM, fmt=fmt)
    ws2.row_dimensions[r].height = 18
    r += 1
r += 1
band(ws2, r, 1, NC, 'TAB MAP')
r += 1
tabmap = [
    ('01 Inputs & Assumptions', 'Yellow cells you own: hours, thresholds, kit list, birthday/Christmas money, overdraft, Australia nights.'),
    ('02 Payslip History', 'Your 7 payslips, NI @8% (>£242/wk), net estimates, the 25.57 h/wk reality check.'),
    ('03 UK Earnings Model', 'Outstanding £667.28 → net; the 5 weeks to 27 Dec; cumulative income-tax check (£0 expected); what lands by departure.'),
    ('04 Funds Available', 'Envelope A–F: realistic/optimistic × with/without the £1,000 overdraft × worst case. THE measuring stick for tabs S1–S9 & 07.'),
    ('05 Confirmed Cost Base', 'VN+TH locked cost built from your workbook, PH/ID segments, Java vs Bali splits, cross-checks (all tie to £4,896.73 ✓).'),
    ('06 Flight Research', 'Every leg priced Nov 2026 with source + range. HKT→BNE £195 vs DPS→BNE £150 vs BNE→LHR £840 — the three swing factors.'),
    ('07 SCENARIO SUMMARY', 'All 9 scenarios ranked against envelopes A–D with verdicts. Bar chart inside. Start here after 10.'),
    ('S1 · S2 · S3 · S4 · S5 · S6 · S7 · S8 · S9', 'Per-scenario route, nights, cost build, 4 envelope gaps, group-legality flag, booking notes. S2 is your friend.'),
    ('10 AS IT IS (VERDICT)', 'Numbered, honest, no softening: what you can afford, what you cannot, what to do by end of November.'),
    ('11 Sources & Method', 'Every figure traced: payslips, workbook, gov.uk NI/PA bands, fare sources Nov 2026, method + disclaimer.'),
]
for tab, desc in tabmap:
    C(ws2, r, 1, tab, bold=True, size=9, color='16324F', border=None)
    ws2.merge_cells(start_row=r, start_column=2, end_row=r, end_column=NC)
    C(ws2, r, 2, desc, size=9, border=None, align='left', wrap=True)
    ws2.row_dimensions[r].height = 24
    r += 1
r += 1
band(ws2, r, 1, NC, 'COLOUR KEY & HOW TO UPDATE')
r += 1
for txt in [
    'Yellow cell = you can change it; every sheet recalculates. Cream = subtotal. Blue = scenario grand total. Red flag = breaks your no-solo rule. Green = funded.',
    'Monthly rhythm till departure: (1) tab 01 → hours & kit list; (2) tab 06 → re-price 3 fares; (3) tab 07 → re-read ranking; (4) tab 10 → re-read the verdict; that is the whole job.',
    'DO NOT trust the PH/ID estimates more than ±15% — they are your friends’ placeholder plan, not quotes. Get actual bed prices when the £2,454.92 locked spend is spent.',
    'If the group halves the Philippines for EVERYONE (not just you), S9 becomes legal and costs the same. Their call.',
]:
    merge_lab(ws2, r, 1, NC, '• ' + txt, size=9, color='26221C', wrap=True)
    ws2.row_dimensions[r].height = 22
    r += 1
footer(ws2, r + 1, NC)
widths(ws2, {'A': 30, 'B': 28, 'C': 28, 'D': 28, 'E': 28, 'F': 28, 'G': 28})

# ================= sheet order, print setup, save =================
order = ['00 READ ME', '01 Inputs & Assumptions', '02 Payslip History', '03 UK Earnings Model', '04 Funds Available',
         '05 Confirmed Cost Base', '06 Flight Research', '07 SCENARIO SUMMARY',
         'S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9',
         '10 AS IT IS (VERDICT)', '11 Sources & Method']
wb._sheets = [wb[nm] for nm in order]
from openpyxl.worksheet.pagebreak import Break, RowBreak

# 05: break pages before major sections so bands never dangle at a page bottom
ws05 = wb['05 Confirmed Cost Base']
ws05.row_breaks = RowBreak()
break_before = ['CONFIRMED VN + TH — ALL-IN GROUND', 'PHILIPPINES — ALL-IN GROUND (full 19 nights)',
                'PHILIPPINES — HALF route', 'INDONESIA — FULL route', 'INDONESIA — ALL-IN GROUND (via MNL, 4 Mar)',
                'JAVA only', 'BALI + GILIS only', 'JUST BALI proper', 'CROSS-CHECK']
for r_ in range(1, ws05.max_row + 1):
    v = ws05.cell(row=r_, column=1).value
    if isinstance(v, str) and any(v.startswith(t) for t in break_before):
        ws05.row_breaks.append(Break(id=r_ - 1))

for ws_ in wb.worksheets:
    ws_.page_setup.orientation = 'landscape'
    ws_.page_setup.paperSize = 5  # legal
    ws_.page_margins.left = 0.35
    ws_.page_margins.right = 0.35
    ws_.page_margins.top = 0.35
    ws_.page_margins.bottom = 0.35
    ws_.page_margins.footer = 0.2
    ws_.page_margins.header = 0.2
    ws_.page_setup.fitToWidth = 1
    ws_.page_setup.fitToHeight = 0
    ws_.sheet_properties.pageSetUpPr.fitToPage = True
    ws_.oddHeader.center.text = '&8SEA 2027 · Budget vs Australia · built 16 Nov 2026'
    ws_.oddHeader.center.size = 8
    ws_.oddFooter.right.text = '&8&P of &N'
    ws_.oddFooter.right.size = 8
    ws_.freeze_panes = ws_.freeze_panes or 'A5'

# keep small tabs to one printed page (after the general loop has run)
for nm in ['00 READ ME', '01 Inputs & Assumptions', '02 Payslip History', '03 UK Earnings Model',
           '04 Funds Available', '06 Flight Research', '10 AS IT IS (VERDICT)', '11 Sources & Method'] + [f'S{i}' for i in range(1, 10)]:
    wb[nm].page_setup.fitToHeight = 1

props = wb.properties
props.title = 'SEA 2027 · Budget vs Australia'
props.creator = 'Cameron'
props.description = 'Budget & itinerary comparison for post-Vietnam/Thailand options with a mandatory Australia leg'

wb.save(OUT)
print('saved', OUT)
