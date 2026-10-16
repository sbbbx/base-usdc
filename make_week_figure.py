"""画「一周基线」图：日内节律、日间差异、金额分布与集中度的一周/单日对照。

输入（data/week/ 下由 fetch_transfers_week.py 生成）：
  summary.json、transfers_windows.csv、week_hourly.csv、week_hist_amount.csv、week_concentration.csv
单日对照用已提交的 data/transfers_sample.csv（2026-10-14–15 那 24 小时的单日采样）；
两张曲线用同一套口径现算，避免口径漂移。
输出 figures/base_usdc_week.{png,svg,pdf}
"""

import json
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE = "#2775CA", "#E8A33D"
OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
WEEK = DATA / "week"
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)
BIN = 0.05  # 金额对数分箱宽度（0.05 十倍程 ≈ 12%）

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

plt.rcParams.update({
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "font.size": 11,
    "axes.titlesize": 12.5,
    "axes.labelsize": 11.5,
    "axes.grid": True,
    "axes.axisbelow": True,
    "grid.color": "#DDDDDD",
    "grid.linewidth": 0.7,
    "axes.edgecolor": "#888888",
    "legend.frameon": False,
})


def concentration(vals, grid):
    """按金额降序，前 f%（f 以百分数计）的转账携带多少金额。与汇总脚本同一口径。"""
    v = np.sort(vals)
    n, sv = len(v), float(np.sum(v))
    out = []
    for f in grid:
        m = int(round(n * f / 100))
        out.append(float(np.sum(v[n - m:]) / sv) if m else 0.0)
    return np.array(out)


def hist_share(vals, edges):
    """金额按 BIN 宽度的 log10 分箱后，占正额笔数的比例（%）。"""
    lg = np.floor(np.log10(vals) / BIN) * BIN
    left = edges[:-1]
    idx = np.rint((lg - left[0]) / BIN).astype(int)
    idx = idx[(idx >= 0) & (idx < len(left))]
    cnt = np.bincount(idx, minlength=len(left))
    return cnt / len(vals) * 100


def main():
    summ = json.loads((WEEK / "summary.json").read_text(encoding="utf-8"))
    win = pd.read_csv(WEEK / "transfers_windows.csv")
    hourly = pd.read_csv(WEEK / "week_hourly.csv").sort_values("local_hour")
    wk_hist = pd.read_csv(WEEK / "week_hist_amount.csv")
    wk_conc = pd.read_csv(WEEK / "week_concentration.csv").sort_values("rank_pct").reset_index(drop=True)
    assert wk_conc["rank_pct"].is_monotonic_increasing, "集中度表的 rank_pct 不是递增，口径不对"
    assert wk_conc["cum_value_share"].is_monotonic_increasing, "集中度表的累计占比不是递增，口径不对"

    day = pd.read_csv(DATA / "transfers_sample.csv", usecols=["usd"])
    day_all = day["usd"].to_numpy()
    day_pos = day_all[day_all > 0]
    day_zero = int((day_all == 0).sum())

    win["rate"] = win["n_logs"] / win["minutes"]
    per_day = pd.DataFrame(summ["per_day"]).sort_values("date_utc").reset_index(drop=True)

    edges = wk_hist["log10_usd"].to_numpy()
    # 一周直方直接读汇总脚本算好的计数，换算成占正额笔数的比例
    wk_share = wk_hist["count"].to_numpy() / int(summ["logs_total"] - summ["n_zero"]) * 100
    day_share = hist_share(day_pos, np.append(edges, edges[-1] + BIN))

    grid = wk_conc["rank_pct"].to_numpy()
    wk_cum = wk_conc["cum_value_share"].to_numpy() * 100
    day_cum = concentration(day_pos, grid) * 100

    fig = plt.figure(figsize=(11, 7.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[0.82, 1.0], hspace=0.5, wspace=0.22)
    axA, axB, axC, axD = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), \
        fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    # ---- A 日内节律 ----
    for i, (d, g) in enumerate(win.groupby("day_offset")):
        g = g.sort_values("local_hour")
        axA.plot(g["local_hour"], g["rate"], color=BLUE, alpha=0.33, lw=1.0, zorder=2,
                 label="7 天各自" if i == 0 else None)
    axA.fill_between(hourly["local_hour"], hourly["rate_min"], hourly["rate_max"],
                     color=BLUE, alpha=0.12, lw=0, zorder=1, label="7 天范围")
    axA.plot(hourly["local_hour"], hourly["rate_mean"], color=BLUE, lw=2.4, marker="o",
             ms=4, zorder=4, label="7 天平均")
    hi = hourly["rate_mean"].idxmax()
    lo = hourly["rate_mean"].idxmin()
    axA.annotate(f"高峰 {hourly.loc[hi, 'rate_mean']:,.0f} 笔/分钟"
                 f"（{int(hourly.loc[hi, 'local_hour']):02d}:00）",
                 (hourly.loc[hi, "local_hour"], hourly.loc[hi, "rate_mean"]),
                 xytext=(-12, -34), textcoords="offset points", ha="right", fontsize=10,
                 bbox=NOTE_BOX, zorder=6)
    axA.annotate(f"低谷 {hourly.loc[lo, 'rate_mean']:,.0f} 笔/分钟"
                 f"（{int(hourly.loc[lo, 'local_hour']):02d}:00）",
                 (hourly.loc[lo, "local_hour"], hourly.loc[lo, "rate_mean"]),
                 xytext=(0, 20), textcoords="offset points", ha="center", fontsize=10,
                 bbox=NOTE_BOX, zorder=6)
    axA.set_xticks(range(0, 24, 3))
    axA.set_xticklabels([f"{h:02d}:00" for h in range(0, 24, 3)])
    axA.set_xlim(-0.6, 23.6)
    axA.set_xlabel("本地时间（UTC+8，整点窗口）")
    axA.set_ylabel("转账笔数（笔/分钟）")
    axA.set_title("日内节律：同一时刻看 7 天", loc="left")

    # ---- B 日间差异 ----
    for i, row in per_day.iterrows():
        g = win[win["day_offset"] == row["day_offset"]]
        wd = date.fromisoformat(row["date_utc"]).weekday()
        if wd >= 5:
            axB.axvspan(i - 0.42, i + 0.42, color="#F2F2F2", lw=0, zorder=1)
        axB.scatter(np.full(len(g), i) + np.linspace(-0.16, 0.16, len(g)), g["rate"],
                    s=14, color=BLUE, alpha=0.45, lw=0, zorder=3)
        axB.plot([i - 0.26, i + 0.26], [g["rate"].mean()] * 2, color=ORANGE, lw=2.2, zorder=4)
    axB.set_xticks(range(len(per_day)))
    axB.set_xticklabels([f"{r['date_utc'][5:]}\n{'一二三四五六日'[date.fromisoformat(r['date_utc']).weekday()]}"
                         for _, r in per_day.iterrows()], fontsize=9.5)
    axB.set_xlim(-0.55, len(per_day) - 0.45)
    axB.set_ylabel("转账笔数（笔/分钟）")
    axB.set_title("日间差异：一天 24 个窗口", loc="left")
    dm = per_day["rate_mean"]
    axB.text(0.02, 0.96, f"7 天日内均值 {dm.min():,.0f}–{dm.max():,.0f} 笔/分钟\n"
                         f"（橙色横线＝各天均值，灰底＝周末）",
             transform=axB.transAxes, va="top", fontsize=9.6, color="#333333", bbox=NOTE_BOX)

    # ---- C 金额分布：一周 vs 单日 ----
    axC.bar(edges, wk_share, width=BIN, align="edge", color=BLUE, alpha=0.9, zorder=3,
            label="一周 168 窗口")
    axC.stairs(day_share, np.append(edges, edges[-1] + BIN), color=ORANGE,
               lw=1.6, zorder=4, label="单日 24 窗口")
    axC.set_yscale("log")
    axC.set_ylim(1e-3, 30)
    axC.set_yticks([1e-3, 1e-2, 1e-1, 1, 10])
    axC.set_yticklabels(["0.001%", "0.01%", "0.1%", "1%", "10%"])
    lo_e = int(np.floor(edges[0])) - 1
    labels = {-6: "0.000001", -5: "$10^{-5}$", -4: "0.0001", -3: "$10^{-3}$",
              -2: "0.01", -1: "0.1", 0: "1", 1: "10", 2: "100", 3: "1 000",
              4: "1 万", 5: "10 万", 6: "100 万", 7: "1 000 万", 8: "1 亿"}
    ticks = [e for e in sorted(labels) if edges[0] - 1e-9 <= e <= edges[-1] + 1e-9 and e % 2 == 0]
    axC.set_xticks(ticks)
    axC.set_xticklabels([labels[e] for e in ticks])
    axC.set_xlabel("单笔金额（美元，对数刻度）")
    axC.set_ylabel("占正额转账笔数比例")
    axC.set_title("金额分布：一周与单日几乎重合", loc="left")
    axC.legend(loc="upper right", fontsize=9.5)
    axC.text(0.02, 0.97, f"一周：中位数 {summ['usd_median']:,.0f}｜P90 {summ['usd_p90']:,.0f}｜"
                         f"P99 {summ['usd_p99']:,.0f}",
             transform=axC.transAxes, fontsize=9.6, color=BLUE, va="top", bbox=NOTE_BOX)
    axC.text(0.02, 0.86, f"单日：中位数 {np.median(day_pos):,.0f}｜P90 {np.percentile(day_pos, 90):,.0f}｜"
                         f"P99 {np.percentile(day_pos, 99):,.0f}",
             transform=axC.transAxes, fontsize=9.6, color=ORANGE, va="top", bbox=NOTE_BOX)


    # ---- D 集中度：一周 vs 单日 ----
    axD.plot(grid, wk_cum, color=BLUE, lw=2.2, zorder=4, label="一周 168 窗口")
    axD.plot(grid, day_cum, color=ORANGE, lw=1.6, ls=(0, (5, 2)), zorder=5, label="单日 24 窗口")
    for x, lab in ((1.0, "前 1%"), (10.0, "前 10%")):
        axD.axvline(x, color="#999999", lw=0.9, ls=(0, (3, 3)), zorder=2)
    axD.set_xscale("log")
    axD.set_xlim(0.001, 100)
    axD.set_ylim(0, 102)
    axD.set_xticks([0.001, 0.01, 0.1, 1, 10, 100])
    axD.set_xticklabels(["0.001%", "0.01%", "0.1%", "1%", "10%", "100%"])
    axD.set_yticks(range(0, 101, 20))
    axD.set_yticklabels([f"{v}%" for v in range(0, 101, 20)])
    axD.set_xlabel("按金额降序的转账比例（对数刻度）")
    axD.set_ylabel("累计金额占比")
    axD.set_title("集中度：尾部结论一周后不变", loc="left")
    axD.legend(loc="lower right", fontsize=9.5)

    def at(grid_arr, cum, f):
        return float(np.interp(f, grid_arr, cum))

    axD.text(0.30, 0.45, f"一周：前 0.1% {at(grid, wk_cum, 0.1):.1f}%｜"
                         f"前 1% {at(grid, wk_cum, 1.0):.1f}%｜前 10% {at(grid, wk_cum, 10.0):.1f}%",
             transform=axD.transAxes, fontsize=9.6, color=BLUE, va="top", bbox=NOTE_BOX)
    axD.text(0.30, 0.34, f"单日：前 0.1% {at(grid, day_cum, 0.1):.1f}%｜"
                         f"前 1% {at(grid, day_cum, 1.0):.1f}%｜前 10% {at(grid, day_cum, 10.0):.1f}%",
             transform=axD.transAxes, fontsize=9.6, color=ORANGE, va="top", bbox=NOTE_BOX)

    cov = summ["coverage"]
    fig.suptitle("Base 链上 USDC：一周采样基线（把 24 小时快照放进 7 天）",
                 x=0.075, ha="left", fontsize=14.5, fontweight="bold", y=0.99)
    fig.text(0.075, 0.936,
             f"{cov['days_done']} 天 × 每天 {summ['plan']['windows_per_day']} 窗口 = {cov['windows_done']} 个采样窗口，"
             f"每窗口 {summ['plan']['blocks_per_window']} 个连续区块（约 100 秒）；"
             f"共 {cov['blocks_total']:,} 区块、{cov['minutes_total']:,.0f} 分钟，占这一周区块数的 {cov['share_of_week_pct']}%",
             fontsize=10.8, color="#333333")
    fig.text(0.075, 0.916,
             "左上：细线＝7 天各自，粗线＝7 天平均，浅带＝7 天范围 ｜ 下排：橙色虚线＝单日采样（图 2）的同口径对照",
             fontsize=9.8, color="#666666")

    fig.text(0.075, 0.075,
             f"数据来源：免 key Base RPC（base.drpc.org 等 6 个端点轮换）的 eth_getLogs，抓取于 {summ['sampled_at_utc8'][:10]}（UTC+8）。",
             fontsize=8.6, color="#444444")
    fig.text(0.075, 0.052,
             "采样口径：每小时抽 1 个窗口、每窗口 50 个连续区块（约 100 秒），7 天共 168 窗口 / 8,400 区块；",
             fontsize=8.6, color="#444444")
    fig.text(0.075, 0.029,
             f"金额以 USDC 计价、未做二次校验；零额转账（一周 {summ['n_zero']:,} 笔、单日 {day_zero:,} 笔）不进分布图；"
             "橙色虚线为单日采样（图 2）的同口径对照。",
             fontsize=8.6, color="#444444")
    fig.subplots_adjust(left=0.075, right=0.975, top=0.885, bottom=0.15)

    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / "figures" / f"base_usdc_week.{ext}", bbox_inches="tight")
    plt.close(fig)

    # ---- 自检与对照数字 ----
    full = summ["plan"]["days"] * summ["plan"]["windows_per_day"]
    assert cov["windows_done"] <= full, "窗口数超过计划"
    if cov["windows_done"] < full:
        print(f"注意：只有 {cov['windows_done']}/{full} 个窗口，先按现有数据出图（补齐后重跑即可覆盖）")
    assert win["minutes"].min() > 0.5, "有窗口不足半分钟"
    d1 = at(grid, day_cum, 1.0)
    print(f"窗口 {cov['windows_done']} 个、{cov['blocks_total']:,} 区块、{cov['minutes_total']:,.0f} 分钟、"
          f"占该周 {cov['share_of_week_pct']}%")
    print(f"日志 {summ['logs_total']:,} 条；笔数均值 {win['rate'].mean():,.0f} 笔/分钟"
          f"（各窗口 {win['rate'].min():,.0f}–{win['rate'].max():,.0f}）")
    print(f"一周：中位数 {summ['usd_median']:,.0f}｜P90 {summ['usd_p90']:,.0f}｜P99 {summ['usd_p99']:,.0f}｜"
          f"最大 {summ['usd_max']:,.0f}｜零额 {summ['n_zero']:,}")
    print(f"单日：中位数 {np.median(day_pos):,.0f}｜P90 {np.percentile(day_pos, 90):,.0f}｜"
          f"P99 {np.percentile(day_pos, 99):,.0f}｜最大 {day_pos.max():,.0f}｜零额 {day_zero:,}")
    print(f"集中度 单日 前 1% = {d1:.2f}%（图 2 里是 92.6%，同口径复算应一致）")
    print(f"日间均值区间 {dm.min():,.0f}–{dm.max():,.0f} 笔/分钟")
    print(f"已写出 figures/base_usdc_week.png（{'/'.join(['png','svg','pdf'])}）")


if __name__ == "__main__":
    main()
