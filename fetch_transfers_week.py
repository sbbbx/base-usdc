"""把「1 天 × 24 窗口」的单日快照扩成「7 天 × 24 窗口」的一周基线。

采样口径（写进图与文）：
- 从链头往前铺 7 天，每天 24 个采样窗口，每窗口 50 个连续区块（Base 约 2 秒/块，即约 100 秒）。
- 共 168 窗口 / 8400 区块；每小时的区块里只取 50 块，占该周区块总数的约 (50/1800) = 2.8%。
- 窗口按「天」优先排列（先 7 天前的 24 小时，再 1 天前的 24 小时），所以中途停下也能得到
  若干「完整日内曲线」，而不会只剩某几天里的零散小时。
- 单次 eth_getLogs 有结果上限（实测约 20000 条），超限自动对半砍窗口。

分两阶段，可续跑：
  抓取阶段  每个窗口写 data/week/w<k>.json，已存在的窗口直接跳过
  汇总阶段  168 个窗口齐全后写 data/week/ 下的 windows / hourly / hist / concentration / summary
            另写 data/week/sample.csv（逐笔明细，体积大，不进仓库）
"""

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

# 免 key 的 Base RPC 端点池。base-rpc.publicnode.com 在累计约 200MB getLogs 后开始返回 403，
# 所以轮换使用并对被拒端点做冷却。2026-10-15 实测可跑 getLogs 的端点如下。
ENDPOINTS = [
    "https://base.drpc.org",
    "https://base.publicnode.com",
    "https://gateway.tenderly.co/public/base",
    "https://base-mainnet.public.blastapi.io",
    "https://base.rpc.thirdweb.com",
    "https://1rpc.io/base",
]
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO = "0x" + "0" * 40
USDC_DECIMALS = 6

DAYS = 7
WINDOWS_PER_DAY = 24
BLOCKS_PER_WINDOW = 50
BLOCKS_PER_HOUR_EST = 1800  # Base 约 2 秒/块

OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
WEEK = DATA / "week"
WEEK.mkdir(parents=True, exist_ok=True)
PLAN = WEEK / "plan.json"

stats = {"requests": 0, "bytes": 0, "seconds": 0.0, "retries": 0, "per_endpoint": {}}
cooldown = {url: 0.0 for url in ENDPOINTS}


def rpc(method, params, timeout=120):
    """按冷却时间排序尝试端点池，任一成功即返回。"""
    global stats
    last_exc = None
    order = sorted(ENDPOINTS, key=lambda u: cooldown[u])
    for i, url in enumerate(order):
        if time.time() < cooldown[url] and i < len(order) - 1:
            continue
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json", "User-Agent": "web3-study/0.2"}
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429, 502, 503, 504):
                cooldown[url] = time.time() + 90
            last_exc = exc
            print(f"    {url.split('//')[1]} → HTTP {exc.code}，换端点", flush=True)
            continue
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_exc = exc
            print(f"    {url.split('//')[1]} → {type(exc).__name__}，换端点", flush=True)
            continue
        dt = time.time() - t0
        stats["requests"] += 1
        stats["bytes"] += len(raw)
        stats["seconds"] += dt
        ep = stats["per_endpoint"].setdefault(url, {"requests": 0, "bytes": 0})
        ep["requests"] += 1
        ep["bytes"] += len(raw)
        return json.loads(raw)
    raise last_exc


def get_logs(start, span):
    """取 [start, start+span-1] 的 Transfer 日志；结果超上限或被限流就缩窗口重试。"""
    delay = 2.0
    while True:
        try:
            msg = rpc(
                "eth_getLogs",
                [{"fromBlock": hex(start), "toBlock": hex(start + span - 1),
                  "address": USDC, "topics": [TOPIC_TRANSFER]}],
            )
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            stats["retries"] += 1
            print(f"    网络错误 {exc} → {delay:.0f}s 后重试", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 30)
            continue
        if "result" in msg:
            return msg["result"], span
        err = str(msg.get("error"))
        stats["retries"] += 1
        if span > 10:
            span = max(10, span // 2)
            print(f"    服务端拒绝（{err[:70]}…）→ 窗口缩到 {span} 块", flush=True)
            time.sleep(1.0)
            continue
        print(f"    {start} 起仍失败：{err}", flush=True)
        time.sleep(delay)
        delay = min(delay * 2, 30)


def to_int(v):
    return v if isinstance(v, int) else int(v, 16)


def addr(topic):
    return "0x" + topic[-40:]


def build_plan(days, per_day, blocks):
    """锚点：链头回退到整点网格，窗口间隔按当天实测块速换算。"""
    print("读链头、算窗口锚点…", flush=True)
    head = to_int(rpc("eth_blockNumber", [])["result"])
    t_head = to_int(rpc("eth_getBlockByNumber", [hex(head), False])["result"]["timestamp"])
    ref = (head - BLOCKS_PER_HOUR_EST) // BLOCKS_PER_HOUR_EST * BLOCKS_PER_HOUR_EST
    t_ref = to_int(rpc("eth_getBlockByNumber", [hex(ref), False])["result"]["timestamp"])
    bpsec = (head - ref) / (t_head - t_ref)
    bph = bpsec * 3600
    windows = []
    for d in range(days):
        for h in range(per_day):
            k = d * per_day + h
            windows.append({
                "index": k,
                "day_offset": d,
                "hour_offset": h,
                "start_block": ref - int(round(k * bph)),
            })
    plan = {
        "endpoints": ENDPOINTS,
        "head_block": head,
        "head_time": t_head,
        "ref_block": ref,
        "ref_time": t_ref,
        "blocks_per_second": round(bpsec, 4),
        "blocks_per_hour": round(bph, 1),
        "days": days,
        "windows_per_day": per_day,
        "blocks_per_window": blocks,
        "windows": windows,
    }
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"链头 {head} @ {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(t_head))}，"
        f"{bpsec:.3f} 块/秒；窗口 0 起点 {windows[0]['start_block']}，"
        f"窗口 {len(windows)-1} 起点 {windows[-1]['start_block']}（"
        f"{time.strftime('%Y-%m-%d %H:%MZ', time.gmtime(t_ref - int(round((len(windows)-1)*bph))*2))} 左右）",
        flush=True,
    )
    return plan


def fetch_window(win, blocks, total):
    k, start = win["index"], win["start_block"]
    logs, span = get_logs(start, blocks)
    rows = []
    for lg in logs:
        frm, to = addr(lg["topics"][1]), addr(lg["topics"][2])
        kind = "mint" if frm == ZERO else ("burn" if to == ZERO else "transfer")
        rows.append([
            to_int(lg["blockTimestamp"]),
            to_int(lg["blockNumber"]),
            frm,
            to,
            round(to_int(lg["data"]) / 10**USDC_DECIMALS, 6),
            kind,
        ])
    rows.sort()
    rec = {
        "window": k,
        "day_offset": win["day_offset"],
        "hour_offset": win["hour_offset"],
        "start_block": start,
        "end_block": start + span - 1,
        "span": span,
        "ts_start": rows[0][0] if rows else None,
        "ts_end": rows[-1][0] if rows else None,
        "transfers": rows,
    }
    (WEEK / f"w{k:03d}.json").write_text(json.dumps(rec), encoding="utf-8")
    if rows:
        print(
            f"  [{k+1:>3}/{total}] 第 {win['day_offset']} 天前 {time.strftime('%m-%d %H:%M', time.gmtime(rows[0][0]))}Z  "
            f"块 {start}  {len(rows):>5} 条", flush=True
        )
    else:
        print(f"  [{k+1:>3}/{total}] 块 {start}–{rec['end_block']}  无日志", flush=True)


def aggregate(plan, blocks):
    """按已抓到的窗口汇总；缺窗口时只报覆盖度，不阻断。"""
    days, per_day = plan["days"], plan["windows_per_day"]
    have, per_window = [], []
    totals = {"n": 0, "usd": 0.0}
    kinds = Counter()
    froms, tos = Counter(), Counter()
    vals = []
    n_zero = n_under1 = 0
    sample = (DATA / "week" / "sample.csv").open("w", newline="", encoding="utf-8")
    sw = csv.writer(sample)
    sw.writerow(["window", "day_offset", "timestamp", "block", "from", "to", "usd", "kind"])

    for win in plan["windows"]:
        k = win["index"]
        path = WEEK / f"w{k:03d}.json"
        if not path.exists():
            continue
        rec = json.loads(path.read_text(encoding="utf-8"))
        rows = rec["transfers"]
        n = len(rows)
        have.append(k)
        v = sorted(r[4] for r in rows)
        wfrom, wto = Counter(r[2] for r in rows), Counter(r[3] for r in rows)
        for r in rows:
            sw.writerow([k, win["day_offset"], *r])
        per_window.append({
            "window": k,
            "day_offset": win["day_offset"],
            "hour_offset": win["hour_offset"],
            "start_block": rec["start_block"],
            "blocks": rec["span"],
            "ts_start": rec["ts_start"],
            "ts_end": rec["ts_end"],
            "utc_hour": time.gmtime(rec["ts_start"]).tm_hour if n else "",
            "local_hour": (time.gmtime(rec["ts_start"]).tm_hour + 8) % 24 if n else "",
            "minutes": round((rec["ts_end"] - rec["ts_start"]) / 60, 2) if n else "",
            "n_logs": n,
            "n_transfer": sum(1 for r in rows if r[5] == "transfer"),
            "n_mint": sum(1 for r in rows if r[5] == "mint"),
            "n_burn": sum(1 for r in rows if r[5] == "burn"),
            "usd_total": round(sum(v), 2),
            "usd_median": round(v[n // 2], 2) if n else "",
            "usd_p90": round(v[int(n * 0.9)], 2) if n else "",
            "usd_p99": round(v[int(n * 0.99)], 2) if n else "",
            "n_zero": sum(1 for x in v if x == 0),
            "uniq_from": len(wfrom),
            "uniq_to": len(wto),
            "top_from_share": round(wfrom.most_common(1)[0][1] / n, 4) if n else "",
        })
        totals["n"] += n
        totals["usd"] += sum(v)
        kinds.update(r[5] for r in rows)
        froms.update(r[2] for r in rows)
        tos.update(r[3] for r in rows)
        vals += v
        n_zero += sum(1 for x in v if x == 0)
        n_under1 += sum(1 for x in v if 0 < x < 1)
    sample.close()

    with (WEEK / "transfers_windows.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_window[0].keys()))
        w.writeheader()
        w.writerows(per_window)

    vals.sort()
    n = len(vals)
    sv = sum(vals)
    # 日内曲线：按本地小时（UTC+8）聚合，给出各天的取值以便画离散带
    hourly = []
    for h in range(24):
        sub = [x for x in per_window if x["local_hour"] == h]
        if not sub:
            continue
        rates = [x["n_logs"] / x["minutes"] for x in sub]
        hourly.append({
            "local_hour": h,
            "windows": len(sub),
            "rate_min": round(min(rates), 1),
            "rate_mean": round(sum(rates) / len(rates), 1),
            "rate_max": round(max(rates), 1),
            "rate_cv": round((sum((r - sum(rates) / len(rates)) ** 2 for r in rates) / len(rates)) ** 0.5
                             / (sum(rates) / len(rates)), 4),
        })
    with (WEEK / "week_hourly.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(hourly[0].keys()))
        w.writeheader()
        w.writerows(hourly)

    # 金额分布：log10 分箱（0.05 十倍程 = 12% 宽度）
    import math
    pos = [x for x in vals if x > 0]
    lo = math.floor(math.log10(min(pos)) * 20) / 20
    hi = math.ceil(math.log10(max(pos)) * 20) / 20
    bins = {}
    for x in pos:
        b = round(math.floor(math.log10(x) * 20) / 20, 4)
        bins[b] = bins.get(b, 0) + 1
    with (WEEK / "week_hist_amount.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["log10_usd", "bin_left_usd", "count"])
        for i in range(int(round((hi - lo) / 0.05)) + 1):
            bb = round(lo + i * 0.05, 4)
            w.writerow([bb, f"{10**bb:.6g}", bins.get(bb, 0)])

    # 集中度：按金额降序的累计占比曲线（对数稀网格，够画图）
    grid = ([0.0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1] +
            [round(x * 0.1, 2) for x in range(2, 21)] +
            [round(float(x), 1) for x in range(3, 21)] +
            [30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0])
    # 集中度：先按金额降序取前 m = round(n·f/100) 笔，看它们占总金额的比例（f 以百分数计）
    out_rows = []
    for rank_pct in grid:
        m = int(round(n * rank_pct / 100))
        share = sum(vals[n - m:]) / sv if m else 0.0
        out_rows.append({"rank_pct": rank_pct, "cum_value_share": round(share, 6)})
    with (WEEK / "week_concentration.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["rank_pct", "cum_value_share"])
        w.writeheader()
        w.writerows(out_rows)

    n_days = len({x["day_offset"] for x in per_window})
    per_day_agg = []
    for d in range(days):
        sub = [x for x in per_window if x["day_offset"] == d]
        if not sub:
            continue
        per_day_agg.append({
            "day_offset": d,
            "date_utc": time.strftime("%Y-%m-%d", time.gmtime(min(x["ts_start"] for x in sub))),
            "windows": len(sub),
            "n_logs": sum(x["n_logs"] for x in sub),
            "rate_mean": round(sum(x["n_logs"] / x["minutes"] for x in sub) / len(sub), 1),
            "usd_total": round(sum(x["usd_total"] for x in sub), 2),
            "usd_median_mean": round(sum(x["usd_median"] for x in sub) / len(sub), 2),
        })

    summary = {
        "per_endpoint": stats["per_endpoint"],
        "sampled_at_utc8": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "plan": {k: plan[k] for k in ("head_block", "head_time", "ref_block", "ref_time",
                                      "blocks_per_second", "blocks_per_hour", "days",
                                      "windows_per_day", "blocks_per_window")},
        "coverage": {
            "windows_expected": len(plan["windows"]),
            "windows_done": len(per_window),
            "days_done": n_days,
            "blocks_total": sum(x["blocks"] for x in per_window),
            "minutes_total": round(sum(x["minutes"] for x in per_window), 2),
            "share_of_week_pct": round(sum(x["blocks"] for x in per_window) /
                                        (7 * 24 * plan["blocks_per_hour"]) * 100, 3),
        },
        "logs_total": n,
        "kinds": dict(kinds),
        "target": USDC,
        "usd_total": round(sv, 2),
        "usd_median": round(vals[n // 2], 2),
        "usd_p90": round(vals[int(n * 0.9)], 2),
        "usd_p99": round(vals[int(n * 0.99)], 2),
        "usd_max": round(vals[-1], 2),
        "n_zero": n_zero,
        "n_under_1usd": n_under1,
        "top_1pct_value_share": round(sum(vals[int(n * 0.99):]) / sv, 4),
        "top_0p1pct_value_share": round(sum(vals[int(n * 0.999):]) / sv, 4),
        "unique_senders": len(froms),
        "unique_receivers": len(tos),
        "top_senders": [{"address": a, "n": c, "share": round(c / n, 4)} for a, c in froms.most_common(10)],
        "top_receivers": [{"address": a, "n": c, "share": round(c / n, 4)} for a, c in tos.most_common(10)],
        "per_day": per_day_agg,
        "requests": stats["requests"],
        "bytes_downloaded": stats["bytes"],
        "rpc_seconds": round(stats["seconds"], 1),
        "server_retries": stats["retries"],
    }
    (WEEK / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=DAYS)
    ap.add_argument("--per-day", type=int, default=WINDOWS_PER_DAY)
    ap.add_argument("--blocks", type=int, default=BLOCKS_PER_WINDOW)
    ap.add_argument("--limit", type=int, default=0, help="只抓前 N 个窗口（冒烟测试用），0 = 全部")
    ap.add_argument("--aggregate-only", action="store_true", help="只汇总，不抓取")
    args = ap.parse_args()

    if PLAN.exists():
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        print(f"沿用已有锚点（链头 {plan['head_block']}，窗口 {len(plan['windows'])} 个）", flush=True)
    else:
        plan = build_plan(args.days, args.per_day, args.blocks)

    if not args.aggregate_only:
        todo = plan["windows"]
        if args.limit:
            todo = todo[:args.limit]
        for win in todo:
            if (WEEK / f"w{win['index']:03d}.json").exists():
                continue
            fetch_window(win, args.blocks, len(plan["windows"]))
            time.sleep(0.3)

    missing = [w["index"] for w in plan["windows"] if not (WEEK / f"w{w['index']:03d}.json").exists()]
    if missing:
        have = len(plan["windows"]) - len(missing)
        print(f"还缺 {len(missing)} 个窗口（已抓 {have}/{len(plan['windows'])}），先按现有数据汇总；重跑本脚本会继续。", flush=True)

    summary = aggregate(plan, args.blocks)
    cov = summary["coverage"]
    print(
        f"\n覆盖：{cov['windows_done']}/{cov['windows_expected']} 窗口、{cov['days_done']} 天、"
        f"{cov['blocks_total']} 区块、{cov['minutes_total']:.0f} 分钟，占该周区块 {cov['share_of_week_pct']}%",
        flush=True,
    )
    print(
        f"日志 {summary['logs_total']:,} 条 / {stats['requests']} 次请求 / "
        f"{stats['bytes']/1024/1024:.0f}MB / {stats['seconds']:.0f}s / 服务端重试 {stats['retries']}",
        flush=True,
    )
    print(
        f"类型 {summary['kinds']}；金额合计 {summary['usd_total']:,.0f} 美元，"
        f"中位数 {summary['usd_median']}、P90 {summary['usd_p90']}、P99 {summary['usd_p99']}、"
        f"最大 {summary['usd_max']:,.0f}",
        flush=True,
    )
    print(
        f"零额 {summary['n_zero']:,} 笔、不足 1 美元 {summary['n_under_1usd']:,} 笔；"
        f"前 0.1% 占 {summary['top_0p1pct_value_share']*100:.1f}%、前 1% 占 {summary['top_1pct_value_share']*100:.1f}%；"
        f"独立发送 {summary['unique_senders']:,} / 接收 {summary['unique_receivers']:,}",
        flush=True,
    )


if __name__ == "__main__":
    main()
