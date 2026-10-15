"""第二张图：Base 上 USDC 转账活动的笔数、金额分布与集中度（24 小时采样）。

读 data/transfers_windows.csv + data/transfers_sample.csv 出图，
落盘 figures/base_usdc_transfers.{png,svg,pdf}。
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, LogLocator

OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
FIG = OUT / "figures"
FIG.mkdir(exist_ok=True)

BLUE = "#2775CA"
ORANGE = "#E8A33D"
GREY = "#666666"
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei"],
    "axes.unicode_minus": False,
    "figure.dpi": 200,
    "savefig.dpi": 200,
})

win = pd.read_csv(DATA / "transfers_windows.csv")
sm = pd.read_csv(DATA / "transfers_sample.csv")
meta = json.loads((DATA / "transfers_summary.json").read_text(encoding="utf-8"))

win["start_dt"] = pd.to_datetime(win["ts_start"], unit="s", utc=True).dt.tz_convert("Asia/Shanghai")
win["end_dt"] = pd.to_datetime(win["ts_end"], unit="s", utc=True).dt.tz_convert("Asia/Shanghai")
sm["dt"] = pd.to_datetime(sm["timestamp"], unit="s", utc=True).dt.tz_convert("Asia/Shanghai")

win["per_min"] = win["n_transfer"] / win["minutes"]
xfer = sm[sm["kind"] == "transfer"]
mint, burn = sm[sm["kind"] == "mint"], sm[sm["kind"] == "burn"]

# ---- 自检：逐窗口条数与逐笔表对得上 ----
assert int(win["n_logs"].sum()) == len(sm), "逐窗口条数与逐笔表不一致"

# ---- 统计量 ----
vals = xfer["usd"].to_numpy()
vals_pos = vals[vals > 0]
n_zero = int((vals == 0).sum())
vals_sorted = np.sort(vals)[::-1]
cum = np.cumsum(vals_sorted) / vals_sorted.sum()
rank = np.arange(1, len(vals_sorted) + 1) / len(vals_sorted)


def share_top(frac):
    k = max(1, int(round(frac * len(vals_sorted))))
    return cum[k - 1]


peak, trough = win.loc[win["per_min"].idxmax()], win.loc[win["per_min"].idxmin()]
bps = meta["plan"]["blocks_per_second"]
coverage = meta["blocks_total"] / (24 * 3600 * bps)
win_min = win["minutes"].mean()
shots = len(sm)

print(f"窗口 {len(win)} 个 × {win['minutes'].iloc[0]:.2f} 分钟 = 采样 {win['minutes'].sum():.1f} 分钟，"
      f"占 24 小时的 {win['minutes'].sum()/1440*100:.2f}%")
print(f"日志 {len(sm):,} 条：转账 {len(xfer):,} / 铸造 {len(mint)} / 销毁 {len(burn)}")
print(f"覆盖区块 {meta['blocks_total']} 个，占 24 小时区块数的 {coverage*100:.2f}%（{bps} 块/秒）")
print(f"笔数：均值 {win['per_min'].mean():.0f} 笔/分钟，区间 {trough['per_min']:.0f}–{peak['per_min']:.0f}"
      f"（{trough['start_dt']:%m-%d %H:%M} / {peak['start_dt']:%m-%d %H:%M}）")
print(f"金额（仅正额）：中位数 {np.median(vals_pos):.2f}，P90 {np.percentile(vals_pos, 90):,.0f}，"
      f"P99 {np.percentile(vals_pos, 99):,.0f}，最大 {vals_pos.max():,.0f}")
print(f"零额与尘埃：{n_zero:,} 笔为 0，{(vals < 1).sum():,} 笔不足 1 美元"
      f"（{np.mean(vals < 1)*100:.1f}%），最小正值 {vals_pos.min():g} 美元")
print(f"集中度：前 0.1% 占 {share_top(0.001)*100:.1f}%，前 1% 占 {share_top(0.01)*100:.1f}%，"
      f"前 10% 占 {share_top(0.10)*100:.1f}%，后 50% 占 {cum[int(len(cum)*0.5)-1]/1:.4f}")
print(f"金额合计：转账 {vals.sum():,.0f}，铸造 {mint['usd'].sum():,.0f}，销毁 {burn['usd'].sum():,.0f}")
print(f"地址：独立发送 {meta['unique_senders']:,}，独立接收 {meta['unique_receivers']:,}；"
      f"最大发送方占比 {meta['top_senders'][0]['share']*100:.1f}%")

# ---- 画图 ----
fig = plt.figure(figsize=(11, 7.6))
gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], hspace=0.46, wspace=0.22)
axA, axB, axC = fig.add_subplot(gs[0, :]), fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

# 面板 A：逐窗口笔数
pos = np.arange(len(win))
axA.bar(pos, win["per_min"], width=0.72, color=BLUE, zorder=3)
axA.set_ylim(0, win["per_min"].max() * 1.16)
axA.set_ylabel("转账笔数（笔/分钟）")
axA.set_xlabel("采样窗口起点（北京时间，UTC+8）")
ticks = list(range(0, len(win), 4))
axA.set_xticks(ticks)
axA.set_xticklabels([f"{win['start_dt'].iloc[i]:%m-%d\n%H:%M}" for i in ticks])
day_breaks = [i for i in range(1, len(win)) if win["start_dt"].iloc[i].date() != win["start_dt"].iloc[i - 1].date()]
for i in day_breaks:
    axA.axvline(i - 0.5, color=GREY, lw=0.8, ls=(0, (4, 3)), zorder=2)
    axA.text(i - 0.42, win["per_min"].max() * 1.14, f"{win['start_dt'].iloc[i]:%m-%d}", fontsize=9, color=GREY)
axA.annotate(
    f"峰值 {peak['per_min']:,.0f} 笔/分钟（{peak['start_dt']:%m-%d %H:%M}）",
    xy=(peak.name, peak["per_min"]), xytext=(peak.name + 1.1, win["per_min"].max() * 0.86),
    fontsize=9.5, color=BLUE, ha="left", arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.9), bbox=NOTE_BOX,
)
axA.annotate(
    f"低谷 {trough['per_min']:,.0f} 笔/分钟（{trough['start_dt']:%m-%d %H:%M}）",
    xy=(trough.name, trough["per_min"]), xytext=(trough.name + 1.1, win["per_min"].max() * 0.42),
    fontsize=9.5, color=GREY, ha="left", arrowprops=dict(arrowstyle="-", color=GREY, lw=0.9), bbox=NOTE_BOX,
)
axA.set_title(
    f"每个采样窗口 {win_min:.2f} 分钟（50 个连续区块），24 个窗口共 {len(sm):,} 条日志",
    fontsize=10.5, color=GREY, pad=8,
)
axA.grid(axis="y", color="#DDDDDD", lw=0.7, zorder=0)
axA.set_axisbelow(True)
for s in ("top", "right"):
    axA.spines[s].set_visible(False)

# 面板 B：单笔金额分布
lo, hi = np.floor(np.log10(vals_pos.min())), np.ceil(np.log10(vals_pos.max()))
bins = np.arange(lo, hi + 0.25, 0.25)
axB.hist(np.log10(vals_pos), bins=bins, color=BLUE, alpha=0.9, zorder=3)
axB.set_yscale("log")
axB.set_xlabel("单笔金额（美元，对数刻度）")
axB.set_ylabel("转账笔数（对数刻度）")
xt = [-6, -4, -2, 0, 2, 4, 6, 8]
axB.set_xticks(xt)
axB.set_xticklabels(["0.000001", "0.0001", "0.01", "1", "100", "1 万", "100 万", "1 亿"], fontsize=8.5)
for q in (50, 90, 99):
    axB.axvline(np.log10(np.percentile(vals_pos, q)), color=ORANGE, lw=1.1, ls=(0, (5, 3)), zorder=4)
axB.text(
    0.02, 0.97,
    f"中位数 {np.median(vals_pos):,.0f} 美元\n"
    f"P90 {np.percentile(vals_pos, 90):,.0f} 美元\n"
    f"P99 {np.percentile(vals_pos, 99):,.0f} 美元\n"
    f"最大单笔 {vals_pos.max()/1e8:,.2f} 亿美元\n"
    f"另有 {n_zero:,} 笔金额为 0，未入图",
    transform=axB.transAxes, fontsize=9.5, color=ORANGE, va="top", ha="left", bbox=NOTE_BOX,
)
axB.grid(axis="y", color="#DDDDDD", lw=0.7, zorder=0)
axB.set_axisbelow(True)
for s in ("top", "right"):
    axB.spines[s].set_visible(False)

# 面板 C：金额集中度
axC.plot(rank, cum, color=BLUE, lw=2.0, zorder=4)
axC.plot([0, 1], [0, 1], color=GREY, lw=1.0, ls=(0, (5, 3)), zorder=3)
axC.set_xscale("log")
axC.set_xlim(1 / len(rank), 1)
axC.set_ylim(0, 1.02)
axC.set_xlabel("按金额降序的转账比例（对数刻度）")
axC.set_ylabel("累计金额占比")
axC.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v*100:.0f}%"))
axC.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
axC.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v*100:g}%"))
for frac in (0.01, 0.10):
    k = int(round(frac * len(cum)))
    axC.plot([frac, frac], [0, cum[k - 1]], color=ORANGE if frac == 0.01 else BLUE, lw=1.0,
             ls=(0, (4, 3)), zorder=3)
axC.text(
    0.44, 0.45,
    f"前 0.1% 的转账 → {share_top(0.001)*100:.1f}% 的金额\n"
    f"前 1% → {share_top(0.01)*100:.1f}% 的金额\n"
    f"前 10% → {share_top(0.10)*100:.1f}% 的金额\n"
    "灰色虚线＝每笔金额相同时的情形",
    transform=axC.transAxes, fontsize=9, color=BLUE, va="top", ha="left", bbox=NOTE_BOX,
)
axC.grid(color="#DDDDDD", lw=0.7, zorder=0)
axC.set_axisbelow(True)
for s in ("top", "right"):
    axC.spines[s].set_visible(False)

fig.suptitle("Base 链上 USDC：转账笔数、金额分布与集中度（24 小时采样）", x=0.055, ha="left", fontsize=15, weight="bold")
fig.text(0.055, 0.082,
         f"数据来源：免 key Base RPC（{meta['endpoints'][0].split('//')[1]} 等 {len(meta['endpoints'])} 个端点轮换）"
         f"的 eth_getLogs，抓取于 {meta['sampled_at_utc8'][:10]}（UTC+8）。",
         fontsize=8.6, color=GREY, va="bottom")
fig.text(0.055, 0.058,
         f"采样口径：每小时 1 个窗口 × 50 个连续区块（{win_min:.2f} 分钟），共 {len(win)} 窗口 / "
         f"{meta['blocks_total']} 区块 / {len(sm):,} 条日志，占这 24 小时区块数的 {coverage*100:.1f}%。",
         fontsize=8.6, color=GREY, va="bottom")
fig.text(0.055, 0.034,
         f"金额以 USDC 计价、未做二次校验；{n_zero:,} 笔零额转账不进金额分布图。",
         fontsize=8.6, color=GREY, va="bottom")
fig.subplots_adjust(left=0.075, right=0.975, top=0.885, bottom=0.165)

png = FIG / "base_usdc_transfers.png"
for ext in ("png", "svg", "pdf"):
    fig.savefig(FIG / f"base_usdc_transfers.{ext}")
plt.close(fig)
print(f"\n已输出 {png}（{png.stat().st_size/1024:.0f}KB）与 .svg/.pdf")
