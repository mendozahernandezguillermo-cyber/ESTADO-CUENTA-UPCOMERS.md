"""
Genera serie_cfd_b7.csv: la serie diaria del trend con los 7 mercados que el
EA opera DE VERDAD, sin el Nasdaq, que se omite por granularidad de lote.

serie_cfd.csv se construyo con los 8 y por eso todas las cifras de EV que he
dado estan infladas. Esta es la serie que corresponde al sistema real.
"""
import pandas as pd

src = open("trend_cfd.py", encoding="utf-8").read().split('E = "=" * 86')[0]
ns = {"__name__": "cfd"}
exec(compile(src, "trend_cfd.py", "exec"), ns)

UNIV_B7 = [m for m in ns["UNIV_B"] if m != "Nasdaq 100"]
_, s2_b7 = ns["construir"](UNIV_B7)

viejo = pd.read_csv("serie_cfd.csv", index_col=0, parse_dates=True)
out = pd.DataFrame({"s1": viejo["s1"]})
out["s2"] = s2_b7.reindex(out.index)
out = out.dropna()
out.index.name = "Date"
out.to_csv("serie_cfd_b7.csv")

print(f"serie_cfd_b7.csv escrito: {len(out)} dias")
print(f"  vol anual s2 con 8 mercados : {viejo['s2'].std()*(252**0.5):.2%}")
print(f"  vol anual s2 con 7 mercados : {out['s2'].std()*(252**0.5):.2%}")
print(f"  Sharpe s2 con 8 : "
      f"{viejo['s2'].mean()/viejo['s2'].std()*(252**0.5):.3f}")
print(f"  Sharpe s2 con 7 : {out['s2'].mean()/out['s2'].std()*(252**0.5):.3f}")
