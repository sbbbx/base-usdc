"""按采样窗口抓 Base 上 USDC 的 Transfer 日志，聚合出转账活动指标。

采样口径（写进图与文）：
- 取链头往前 24 小时，每小时 1 个采样窗口，每窗口 50 个连续区块（约 100 秒）。
- 共 24 窗口 / 1200 区块，占这 24 小时区块总数的约 2.8%。
- 单次 eth_getLogs 有结果上限（实测约 20000 条），超限自动对半砍窗口。

分两阶段，可续跑：
  抓取阶段  每个窗口写 data/windows/w<k>.json，已存在的窗口直接跳过
  汇总阶段  24 个窗口齐全后写 data/transfers_windows.csv / transfers_sample.csv / transfers_summary.json
"""

import csv
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

# 免 key 的 Base RPC 端点池。base-rpc.publicnode.com 在累计约 200MB getLogs 后开始返回
# 403，所以轮换使用并对被拒端点做冷却。2026-10-15 实测可跑 getLogs 的端点如下。
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

HOURS = 24
BLOCKS_PER_WINDOW = 50
USDC_DECIMALS = 6

OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
WIN = DATA / "windows"
WIN.mkdir(parents=True, exist_ok=True)
PLAN = WIN / "plan.json"

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
            url, data=body, headers={"Content-Type": "application/json", "User-Agent": "web3-study/0.1"}
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


def build_plan():
    print("读链头、算窗口锚点…", flush=True)
    head = to_int(rpc("eth_blockNumber", [])["result"])
    ref = head - 43200  # Base 约 2 秒/块，先粗估 24 小时前
    t_head = to_int(rpc("eth_getBlockByNumber", [hex(head), False])["result"]["timestamp"])
    t_ref = to_int(rpc("eth_getBlockByNumber", [hex(ref), False])["result"]["timestamp"])
    bpsec = (head - ref) / (t_head - t_ref)
    bph = bpsec * 3600
    plan = {
        "endpoints": ENDPOINTS,
        "head_block": head,
        "head_time": t_head,
        "ref_block": ref,
        "ref_time": t_ref,
        "blocks_per_second": round(bpsec, 4),
        "blocks_per_hour": round(bph, 1),
        "hours": HOURS,
        "blocks_per_window": BLOCKS_PER_WINDOW,
        "windows": {str(k): {"start_block": ref + int(k * bph)} for k in range(HOURS)},
    }
    PLAN.write_text(json.dumps(plan, indent=2), encoding="utf-8")
    print(
        f"链头 {head} @ {time.strftime('%Y-%m-%d %H:%M:%SZ', time.gmtime(t_head))}，"
        f"{bpsec:.3f} 块/秒 → 窗口间隔 {bph:.0f} 块", flush=True
    )
    return plan


def fetch_window(k, start):
    logs, span = get_logs(start, BLOCKS_PER_WINDOW)
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
    win = {
        "window": k,
        "start_block": start,
        "end_block": start + span - 1,
        "span": span,
        "ts_start": rows[0][0] if rows else None,
        "ts_end": rows[-1][0] if rows else None,
        "transfers": rows,
    }
    (WIN / f"w{k:02d}.json").write_text(json.dumps(win), encoding="utf-8")
    if rows:
        print(
            f"  窗口 {k:>2}/23  {time.strftime('%m-%d %H:%M', time.gmtime(rows[0][0]))}–"
            f"{time.strftime('%H:%M', time.gmtime(rows[-1][0]))}Z  块 {start}–{win['end_block']}  "
            f"{len(rows):>5} 条", flush=True
        )
    else:
        print(f"  窗口 {k:>2}/23  块 {start}–{win['end_block']}  无日志", flush=True)


def aggregate(plan):
    all_rows, per_window = [], []
    for k in range(HOURS):
        win = json.loads((WIN / f"w{k:02d}.json").read_text(encoding="utf-8"))
        rows = win["transfers"]
        vals = sorted(r[4] for r in rows)
        froms, tos = Counter(r[2] for r in rows), Counter(r[3] for r in rows)
        n = len(rows)
        per_window.append({
            "window": k,
            "start_block": win["start_block"],
            "end_block": win["end_block"],
            "blocks": win["span"],
            "ts_start": win["ts_start"],
            "ts_end": win["ts_end"],
            "minutes": round((win["ts_end"] - win["ts_start"]) / 60, 2) if n else "",
            "n_logs": n,
            "n_transfer": sum(1 for r in rows if r[5] == "transfer"),
            "n_mint": sum(1 for r in rows if r[5] == "mint"),
            "n_burn": sum(1 for r in rows if r[5] == "burn"),
            "usd_total": round(sum(vals), 2),
            "usd_median": round(vals[n // 2], 2) if n else "",
            "usd_mean": round(sum(vals) / n, 2) if n else "",
            "uniq_from": len(froms),
            "uniq_to": len(tos),
            "top_from_share": round(froms.most_common(1)[0][1] / n, 4) if n else "",
        })
        all_rows += [(k, *r) for r in rows]

    with (DATA / "transfers_windows.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(per_window[0].keys()))
        w.writeheader()
        w.writerows(per_window)
    with (DATA / "transfers_sample.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["window", "timestamp", "block", "from", "to", "usd", "kind"])
        w.writerows(all_rows)

    vals = sorted(r[5] for r in all_rows)
    froms, tos, kinds = Counter(r[3] for r in all_rows), Counter(r[4] for r in all_rows), Counter(r[6] for r in all_rows)
    n = len(all_rows)
    summary = {
        "endpoints": ENDPOINTS,
        "per_endpoint": stats["per_endpoint"],
        "sampled_at_utc8": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "plan": {k: plan[k] for k in ("head_block", "head_time", "ref_block", "ref_time", "blocks_per_second", "blocks_per_hour", "hours", "blocks_per_window")},
        "windows": len(per_window),
        "blocks_total": sum(x["blocks"] for x in per_window),
        "logs_total": n,
        "kinds": dict(kinds),
        "target": USDC,
        "usd_total": round(sum(vals), 2),
        "usd_median": round(vals[n // 2], 2),
        "usd_p90": round(vals[int(n * 0.9)], 2),
        "usd_p99": round(vals[int(n * 0.99)], 2),
        "usd_max": round(vals[-1], 2),
        "top_1pct_value_share": round(sum(vals[int(n * 0.99):]) / sum(vals), 4),
        "unique_senders": len(froms),
        "unique_receivers": len(tos),
        "top_senders": [{"address": a, "n": c, "share": round(c / n, 4)} for a, c in froms.most_common(10)],
        "top_receivers": [{"address": a, "n": c, "share": round(c / n, 4)} for a, c in tos.most_common(10)],
        "requests": stats["requests"],
        "bytes_downloaded": stats["bytes"],
        "rpc_seconds": round(stats["seconds"], 1),
        "server_retries": stats["retries"],
    }
    (DATA / "transfers_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main():
    if PLAN.exists():
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        print(f"沿用已有锚点（链头 {plan['head_block']}，窗口间隔 {plan['blocks_per_hour']} 块）", flush=True)
    else:
        plan = build_plan()

    for k in range(HOURS):
        if (WIN / f"w{k:02d}.json").exists():
            continue
        fetch_window(k, plan["windows"][str(k)]["start_block"])
        time.sleep(0.3)

    missing = [k for k in range(HOURS) if not (WIN / f"w{k:02d}.json").exists()]
    if missing:
        print(f"还缺窗口 {missing}，先不汇总；重跑本脚本会继续。", flush=True)
        return

    summary = aggregate(plan)
    print(
        f"\n完成：{summary['logs_total']} 条日志 / {summary['blocks_total']} 区块，"
        f"{stats['requests']} 次请求 / {stats['bytes']/1024/1024:.0f}MB / {stats['seconds']:.0f}s，"
        f"服务端重试 {stats['retries']} 次", flush=True
    )
    print(
        f"类型 {summary['kinds']}；金额合计 {summary['usd_total']:,.0f} 美元，"
        f"中位数 {summary['usd_median']}、P90 {summary['usd_p90']}、P99 {summary['usd_p99']}；"
        f"独立发送地址 {summary['unique_senders']} / 接收地址 {summary['unique_receivers']}", flush=True
    )


if __name__ == "__main__":
    main()
