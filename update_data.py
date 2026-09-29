"""Fetch NOAA CPC Nino 3.4 data, compute ENSO indices, write data.json."""
import re, json, urllib.request, datetime as dt
from collections import defaultdict

BASE = "https://www.cpc.ncep.noaa.gov/data/indices/"

def get(name):
    req = urllib.request.Request(BASE + name, headers={"User-Agent": "enso-site"})
    return urllib.request.urlopen(req, timeout=60).read().decode()

# 1) Official ONI (ERSSTv5, 3-month running mean). Columns: SEAS YR TOTAL ANOM
oni = []
for i, line in enumerate(get("oni.ascii.txt").splitlines()[1:]):
    p = line.split()
    if len(p) == 4:
        season, year, anom = p[0], int(p[1]), float(p[3])
        center = ["DJF","JFM","FMA","MAM","AMJ","MJJ","JJA","JAS","ASO","SON","OND","NDJ"].index(season) + 1
        oni.append({"m": f"{year}-{center:02d}", "s": season, "a": anom})

# 2) Weekly OISST Nino 3.4 anomalies (base 1991-2020), since 1990.
# Each row: date, then (SST, anomaly) pairs for Nino1+2, 3, 34, 4 -> we want the 3rd pair.
weekly = []
for line in get("wksst9120.for").splitlines():
    m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})(.*)", line)
    if not m:
        continue
    pairs = re.findall(r"(\d{2}\.\d)\s*(-?\d\.\d)", m.group(2))
    if len(pairs) >= 3:
        d = dt.datetime.strptime(m.group(1), "%d%b%Y").strftime("%Y-%m-%d")
        weekly.append({"d": d, "a": float(pairs[2][1])})

# 3) "Live" ONI-style index: monthly mean of weekly anomalies -> 3-month running mean
by_month = defaultdict(list)
for w in weekly:
    by_month[w["d"][:7]].append(w["a"])
months = sorted(by_month)
monthly = {k: sum(v) / len(v) for k, v in by_month.items()}
live = []
for i in range(1, len(months) - 1):
    a, b, c = months[i - 1], months[i], months[i + 1]
    live.append({"m": b, "a": round((monthly[a] + monthly[b] + monthly[c]) / 3, 2)})
# latest (partial) months: trailing 3-month mean ending at the newest month
last3 = months[-3:]
trailing = round(sum(monthly[k] for k in last3) / len(last3), 2)

json.dump({
    "updated": dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    "oni": oni,
    "weekly": weekly,
    "live_oni": live,
    "trailing_3m": {"months": last3, "value": trailing},
}, open("data.json", "w"), separators=(",", ":"))
print("ok", len(oni), len(weekly), trailing)
