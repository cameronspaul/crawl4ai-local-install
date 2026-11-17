import formulas, logging
logging.disable(logging.CRITICAL)
xl = formulas.ExcelModel().loads('SEA_2027_Budget_Comparison.xlsx').finish()
sol = xl.calculate()
print('cells computed:', len(sol))
errs = {}
for k, v in sol.items():
    sv = str(v)
    for bad in ('#REF', '#VALUE', '#DIV', '#NAME', '#NUM'):
        if bad in sv:
            errs.setdefault(bad, []).append(k)
for bad, keys in errs.items():
    print(bad, len(keys), keys[:8])
if not errs:
    print('errors: NONE')
