"""图 5 抓取：Base 上各美元稳定币的逐日流通量（按资产 id 取 /stablecoin/{id}）。

- 只抓「当期快照 ≥ MIN_USD」的资产，其余归入「其他」；快照日与图 1 对齐
  （取 data/base_stablecoins_daily.csv 的最后一天，避免不同图用不同快照）。
- 只用标准库，产物：data/base_composition.csv（date,symbol,usd）+ data/composition_meta.json。
"""
import csv
import json
import time
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
API = "https://stablecoins.llama.fi"
MIN_USD = 5_000_000
MAX_DAYS = 5000
RETRY = 3


def get_json(url):
    last = None
    for _ in range(RETRY):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                return json.load(resp)
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(3)
    raise SystemExit(f"抓取失败 {url}: {last}")


def read_rows(path):
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main():
    snap = read_rows(DATA / "base_stablecoins_now.csv")
    total_rows = read_rows(DATA / "base_stablecoins_daily.csv")
    snap_date = total_rows[-1]["date"]  # 与图 1 同一天
    picked = [r for r in snap if float(r["circulating_usd"]) >= MIN_USD]
    picked.sort(key=lambda r: -float(r["circulating_usd"]))
    print(f"快照日 {snap_date}；命中资产 {len(picked)} 个（阈值 {MIN_USD:,} 美元）")

    series = {}
    for row in picked:
        pid, sym = int(row["id"]), row["symbol"]
        blob = get_json(f"{API}/stablecoin/{pid}")
        tokens = (blob.get("chainBalances", {}).get("Base") or {}).get("tokens", [])
        pts = []
        for t in tokens:
            day = time.strftime("%Y-%m-%d", time.gmtime(t["date"]))
            if day > snap_date:
                continue
            pts.append((day, float((t.get("circulating") or {}).get("peggedUSD") or 0.0)))
        series[sym] = dict(pts)
        print(f"  {sym:9s} id={pid:4d}  {len(pts):5d} 天  {pts[0][0]}..{pts[-1][0]}"
              f"  快照值 {dict(pts).get(snap_date, 0):>16,.0f}（快照表 {float(row['circulating_usd']):>16,.0f}）")

    dates = sorted({d for s in series.values() for d in s})
    out = DATA / "base_composition.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "symbol", "usd"])
        for sym in series:
            for d in dates:
                if d in series[sym]:
                    w.writerow([d, sym, f"{series[sym][d]:.6f}"])
    meta = {
        "fetched_at_utc8": time.strftime("%Y-%m-%dT%H:%M:%S+08:00", time.localtime()),
        "snapshot_date": snap_date,
        "min_usd": MIN_USD,
        "assets": {s: {"id": int(r["id"]), "first_day": min(series[s])}
                   for s, r in zip(series, picked)},
        "source": f"{API}/stablecoin/{{id}} 的 chainBalances.Base.tokens[]",
        "rows": sum(len(s) for s in series.values()),
    }
    (DATA / "composition_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"写出 {out.name}：{meta['rows']} 行 / {len(series)} 个资产 / 快照日 {snap_date}")


if __name__ == "__main__":
    main()
