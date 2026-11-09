"""Edition-based start years from bpresence.py output.

first = earliest edition from which the footprint stays drawn (one miss allowed, last edition must
draw it); start = midpoint(previous edition, first) - or, drawn on the first edition, 'by' that
edition (start left to the caller). Cells: 'P..' present, '-..' absent, '' not covered.
"""
import pandas as pd


def first_drawn(row, eds):
    vals = []
    for e in eds:
        v = row.get(e)
        if isinstance(v, str) and v:
            vals.append(v.startswith("P"))
        else:
            vals.append(None)
    # the last covered edition must draw it
    cov = [k for k, v in enumerate(vals) if v is not None]
    if not cov:
        return None, None, None
    if not vals[cov[-1]]:
        # drawn earlier but not on the last edition -> rebuilt / demolished; report the last drawn
        last = max((k for k in cov if vals[k]), default=None)
        return None, None, (eds[last] if last is not None else None)
    for k in cov:
        later = [vals[j] for j in cov if j >= k]
        if vals[k] and sum(1 for v in later if not v) <= 1:
            prev = [j for j in cov if j < k]
            return eds[k], (eds[prev[-1]] if prev else None), eds[cov[-1]]
    return None, None, None


def table(csv, eds, years):
    d = pd.read_csv(csv, dtype=str, keep_default_na=False)
    out = []
    for _, r in d.iterrows():
        f, prev, last = first_drawn(r, eds)
        est = None
        if f is not None and prev is not None:
            est = (years[f] + years[prev]) / 2
        out.append(dict(id=r["id"], name=r["name"], area_m2=float(r["area_m2"]), lon=float(r["lon"]),
                        lat=float(r["lat"]), first=years.get(f), prev=years.get(prev), last=years.get(last),
                        est=est, cells=" ".join(r[e] or "nc" for e in eds)))
    return pd.DataFrame(out)
