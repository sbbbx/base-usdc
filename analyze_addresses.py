"""按「地址」口径统计一周样本：集中度、活跃度分档、自转成分与净流量。

与前几张图的区别：图 2/图 3 的集中度都是「按笔」（单笔美元金额排序），这张图
换成「按地址」（同一地址在样本期内的合计金额排序），回答两件事：
  1) 样本期里到底有多少个地址在动 USDC，大额是不是少数地址自己刷出来的；
  2) 把双向自转（A→B 同时 B→A）剔掉之后，对外的净流量长什么样。

输入 data/week/sample.csv（168 窗口 730,778 条 Transfer 日志），输出
data/address_stats.json 与 data/address_curve.csv。用法：python -u analyze_addresses.py
"""
import csv
import json
import math
import time
from array import array
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path("data")
WEEK = DATA / "week"
ZERO = "0x" + "0" * 40
BUCKETS = [(1, 1), (2, 10), (11, 100), (101, 1000), (1001, 10 ** 9)]
BUCKET_LABELS = ["1 笔", "2–10 笔", "11–100 笔", "101–1,000 笔", ">1,000 笔"]  # 指「参与的转账笔数」


def gini(vals):
    """升序序列的基尼系数（0 = 完全平均，1 = 全部集中在一点）。"""
    n = len(vals)
    s = sum(vals)
    if n == 0 or s == 0:
        return 0.0
    acc = 0.0
    for i, v in enumerate(vals, 1):
        acc += (2 * i - n - 1) * v
    return acc / (n * s)


def top_shares(vals_desc, total, marks):
    """按降序排列的值，取「前 N / 前 p%」的累计占比。"""
    n = len(vals_desc)
    out = {}
    cum = 0.0
    for i, v in enumerate(vals_desc, 1):
        cum += v
        if i in marks:
            out[str(i)] = round(cum / total, 6)
    for pct in (0.0001, 0.001, 0.01, 0.1):
        k = max(1, int(round(n * pct)))
        out[f"top_{pct * 100:g}pct"] = round(sum(vals_desc[:k]) / total, 6)
    return out


def lorenz(vals_desc):
    """累计份额曲线：返回 (线性 1% 步长) 与 (对数刻度 150 点) 两套采样。"""
    n = len(vals_desc)
    total = sum(vals_desc)
    lin, log = [], []
    log_ranks = {max(1, int(round(math.exp(math.log(1) + i * (math.log(n) - math.log(1)) / 149)))) for i in range(150)}
    lin_ranks = {max(1, int(round(n * f))) for f in [i / 100 for i in range(1, 101)]}
    want = sorted(log_ranks | lin_ranks)
    cum = 0.0
    j = 0
    for i, v in enumerate(vals_desc, 1):
        cum += v
        if j < len(want) and i == want[j]:
            pt = [i, round(cum / total, 6)]
            if i in log_ranks:
                log.append(pt)
            if i in lin_ranks:
                lin.append([round(i / n, 6), round(cum / total, 6)])
            j += 1
    return lin, log


def main():
    t0 = time.time()
    rows = 0
    kinds = Counter()
    usd_total = 0.0
    amounts = array("d")
    cnt = Counter()
    vol = defaultdict(float)
    vol_sent = defaultdict(float)
    vol_recv = defaultdict(float)
    n_sent = Counter()
    n_recv = Counter()
    directed = defaultdict(float)
    pairs_both = defaultdict(lambda: [0.0, 0.0])   # 无序对 -> [a→b 金额, b→a 金额]
    win_rev = 0.0            # 同一 100 秒窗口内出现反向的金额（取两侧较小值）
    block_rev = 0.0          # 同一区块（同秒）内出现反向的金额
    per_window = defaultdict(lambda: {"pairs": {}, "blocks": defaultdict(dict)})
    mint_usd = burn_usd = 0.0

    with (WEEK / "sample.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows += 1
            usd = float(r["usd"])
            amounts.append(usd)
            usd_total += usd
            kind = r["kind"]
            kinds[kind] += 1
            if kind == "mint":
                mint_usd += usd
            elif kind == "burn":
                burn_usd += usd
            a, b = r["from"], r["to"]
            if a != ZERO:
                cnt[a] += 1
                vol[a] += usd
                vol_sent[a] += usd
                n_sent[a] += 1
            if b != ZERO:
                cnt[b] += 1
                vol[b] += usd
                vol_recv[b] += usd
                n_recv[b] += 1
            directed[(a, b)] += usd
            if a != ZERO and b != ZERO and a != b:
                key = (a, b) if a < b else (b, a)
                slot = pairs_both[key]
                slot[0 if key[0] == a else 1] += usd
                w = per_window[r["window"]]
                w["pairs"][key] = w["pairs"].get(key, [0.0, 0.0])
                s2 = w["pairs"][key]
                idx = 0 if key[0] == a else 1
                s2[idx] += usd
                blk = w["blocks"][r["block"]]
                blk[key] = blk.get(key, [0.0, 0.0])
                blk[key][idx] += usd

    for w in per_window.values():
        for lo, hi in w["pairs"].values():
            win_rev += min(lo, hi)
        for blk in w["blocks"].values():
            for lo, hi in blk.values():
                block_rev += min(lo, hi)

    part_total = sum(vol.values())      # 每笔转账在两端各计一次，故约为 usd_total 的两倍
    sent_total = sum(vol_sent.values())
    addr_vals = sorted(vol.values(), reverse=True)
    sent_vals = sorted(vol_sent.values(), reverse=True)
    amounts_desc = sorted(amounts, reverse=True)
    by_addr_lin, by_addr_log = lorenz(addr_vals)
    by_tx_lin, by_tx_log = lorenz(amounts_desc)

    bucket_rows = []
    for (lo, hi), label in zip(BUCKETS, BUCKET_LABELS):
        n = sum(1 for a, c in cnt.items() if lo <= c <= hi)
        v = sum(vol[a] for a, c in cnt.items() if lo <= c <= hi)
        bucket_rows.append({"label": label, "addresses": n,
                            "addr_share": round(n / len(cnt), 6),
                            "usd": round(v, 2), "usd_share": round(v / part_total, 6)})

    net = {a: vol_recv[a] - vol_sent[a] for a in vol}
    top_in = sorted(net.items(), key=lambda kv: -kv[1])[:12]
    top_out = sorted(net.items(), key=lambda kv: kv[1])[:12]

    bidir_pairs = [k for k, v in pairs_both.items() if v[0] > 0 and v[1] > 0]
    bidir_usd = sum(min(v[0], v[1]) for v in pairs_both.values())
    biggest_pair = max(pairs_both.items(), key=lambda kv: -min(kv[1][0], kv[1][1])) if pairs_both else None

    stats = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "data/week/sample.csv",
        "sample": {"logs": rows, "windows": len(per_window), "usd_total": round(usd_total, 2),
                   "kinds": dict(kinds), "unique_addresses": len(cnt),
                   "unique_senders": len(n_sent), "unique_receivers": len(n_recv),
                   "mint_usd": round(mint_usd, 2), "burn_usd": round(burn_usd, 2)},
        "by_address": {"basis": "参与额（收 + 发；每笔转账在两端各计一次）",
                       "part_total": round(part_total, 2),
                       "gini": round(gini(sorted(vol.values())), 4),
                       "top": top_shares(addr_vals, part_total, {10, 100, 1000, 10000}),
                       "top_sent_only": top_shares(sent_vals, sent_total, {10, 100, 1000, 10000}),
                       "sent_total": round(sent_total, 2),
                       "mean_usd": round(part_total / len(cnt), 2),
                       "median_usd": round(addr_vals[len(addr_vals) // 2], 2),
                       "buckets": bucket_rows},
        "by_transfer": {"gini": round(gini(sorted(amounts)), 4),
                        "top": top_shares(amounts_desc, usd_total, {100, 1000, 10000, 100000}),
                        "median_usd": round(amounts_desc[len(amounts_desc) // 2], 2)},
        "churn": {"pairs_total": len(directed), "pairs_both": len(bidir_pairs),
                  "both_usd": round(bidir_usd, 2),
                  "both_share": round(bidir_usd / usd_total, 6),
                  "window_rev_usd": round(win_rev, 2), "window_rev_share": round(win_rev / usd_total, 6),
                  "block_rev_usd": round(block_rev, 2), "block_rev_share": round(block_rev / usd_total, 6),
                  "biggest_pair": ({"lo": biggest_pair[0][0], "hi": biggest_pair[0][1],
                                    "ab": round(biggest_pair[1][0], 2), "ba": round(biggest_pair[1][1], 2),
                                    "matched": round(min(biggest_pair[1]), 2)} if biggest_pair else None)},
        "net": {"in": [{"address": a, "usd": round(v, 2), "n_recv": n_recv[a], "vol": round(vol[a], 2)} for a, v in top_in],
                "out": [{"address": a, "usd": round(-v, 2), "n_sent": n_sent[a], "vol": round(vol[a], 2)} for a, v in top_out],
                "max_in": round(top_in[0][1], 2) if top_in else 0.0,
                "max_out": round(-top_out[0][1], 2) if top_out else 0.0},
        "top_addresses": [{"address": a, "n": cnt[a], "sent": round(vol_sent[a], 2), "recv": round(vol_recv[a], 2),
                           "net": round(vol_recv[a] - vol_sent[a], 2),
                           "share": round(vol[a] / part_total, 6)} for a in sorted(vol, key=lambda x: -vol[x])[:15]],
    }

    (DATA / "address_stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    with (DATA / "address_curve.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["basis", "kind", "rank_or_frac", "cum_share"])
        for pt in by_addr_lin:
            w.writerow(["address", "lin", pt[0], pt[1]])
        for pt in by_addr_log:
            w.writerow(["address", "log_rank", pt[0], pt[1]])
        for pt in by_tx_lin:
            w.writerow(["transfer", "lin", pt[0], pt[1]])
        for pt in by_tx_log:
            w.writerow(["transfer", "log_rank", pt[0], pt[1]])

    s = stats
    print(f"[{time.time() - t0:.1f}s] 日志 {rows:,} 条 / 金额 {usd_total:,.0f} 美元 / 地址 {len(cnt):,} 个")
    pa = s["by_address"]
    print(f"  按地址（参与额合计 {pa['part_total']:,.0f}）：基尼 {pa['gini']} 中位 {pa['median_usd']:,.0f} 美元 "
          f"前 10 {pa['top']['10']:.1%} 前 100 {pa['top']['100']:.1%} "
          f"前 1,000 {pa['top']['1000']:.1%} 前 1 万 {pa['top']['10000']:.1%}"
          f" | 只算发起：前 100 {pa['top_sent_only']['100']:.1%}")
    print("  前 5 地址：" + "  ".join(f"{x['address'][:10]}… {x['share']:.1%}/{x['n']:,} 笔" for x in s["top_addresses"][:5]))
    print(f"  按笔：  基尼 {s['by_transfer']['gini']} 中位 {s['by_transfer']['median_usd']:,.0f} 美元 "
          f"前 1 万笔 {s['by_transfer']['top']['10000']:.1%}")
    for b in s["by_address"]["buckets"]:
        print(f"  {b['label']:>10}：{b['addresses']:>7,} 个地址（{b['addr_share']:>6.1%}）  金额 {b['usd']:>16,.0f}（{b['usd_share']:>6.1%}）")
    c = s["churn"]
    print(f"  自转：双向对 {c['pairs_both']:,} / 总对 {c['pairs_total']:,}；双向对可匹配额 {c['both_usd']:,.0f}（{c['both_share']:.1%}）")
    print(f"        同窗口反向 {c['window_rev_usd']:,.0f}（{c['window_rev_share']:.1%}）  同秒反向 {c['block_rev_usd']:,.0f}（{c['block_rev_share']:.1%}）")
    def head(rows):
        return [(x["address"][:10], format(x["usd"], ",.0f")) for x in rows[:3]]
    print("  净流入前三：" + str(head(s["net"]["in"])))
    print("  净流出前三：" + str(head(s["net"]["out"])))


if __name__ == "__main__":
    main()
