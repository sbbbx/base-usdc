"""画「跨链桥通道」图：桥入 USDC 的存量、占比、月度净变化，以及 minted 缺失日的口径陷阱。

输入：data/usdc_base_daily.csv（由 fetch_data.py 抓的 DefiLlama 逐日序列，本图不再新增抓取）。
口径：桥入存量 = circulating − (minted − unreleased)，与 DefiLlama 的 bridgedTo 字段一致；
      minted 字段在 2023-12-20 才有，且之后仍有缺失日（缺失日会被算成「全部靠桥」的假值），
      本图把缺失日单列在下排右面板，其余统计一律剔除这些日子、按月度取每月最后一个有效日。
输出：figures/base_usdc_bridge.{png,svg,pdf}
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BLUE, ORANGE, GREY = "#2775CA", "#E8A33D", "#9AA0A6"
OUT = Path(__file__).resolve().parent
DATA = OUT / "data"
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)
NATIVE_START = pd.Timestamp("2023-12-20")  # minted 字段从这天起有值

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


def year_axis(ax, x0, x1, first_label=None):
    """横轴只留年份刻度（可选再带一个起点标签），避免日期标签互相压住。"""
    ticks = [pd.Timestamp(f"{y}-01-01") for y in range(x0.year + 1, x1.year + 1)]
    labels = [str(t.year) for t in ticks]
    if first_label:
        ticks, labels = [x0] + ticks, [first_label] + labels
    ax.set_xticks(ticks)
    ax.set_xticklabels(labels)
    ax.set_xlim(x0 - pd.Timedelta(days=25), x1 + pd.Timedelta(days=25))


def main():
    df = pd.read_csv(DATA / "usdc_base_daily.csv", parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    df["native"] = (df["minted_usd"].fillna(0) - df["unreleased_usd"].fillna(0)).clip(lower=0)
    df["bridged"] = df["circulating_usd"] - df["native"]

    # minted 缺失日：2023-12-20 之前是正常的（那时只能靠桥），之后缺失会把整条流通量误记成桥入
    bad = df[(df["date"] >= NATIVE_START) & df["minted_usd"].isna()]["date"]
    keep = df[~df["date"].isin(bad)].copy()
    keep["share"] = keep["bridged"] / keep["circulating_usd"] * 100

    err = float((keep["native"] + keep["bridged"] - keep["circulating_usd"]).abs().max())
    assert err < 1e-6, f"原生 + 桥入 与流通量对不上，最大误差 {err}"

    mon = keep.set_index("date").resample("ME").last()
    mon["net"] = mon["bridged"].diff()
    fetched = json.loads((DATA / "meta.json").read_text(encoding="utf-8")).get("fetched_at_utc8", "")[:10]
    peak_i = keep["bridged"].idxmax()
    first, last = keep.iloc[0], keep.iloc[-1]
    net_cum = last["bridged"] - first["bridged"]
    drop_peak = (last["bridged"] - keep.loc[peak_i, "bridged"]) / keep.loc[peak_i, "bridged"] * 100
    circ_net = last["circulating_usd"] - first["circulating_usd"]
    neg_months = int((mon["net"].dropna() < 0).sum())

    fig = plt.figure(figsize=(11, 7.8))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.0], hspace=0.46, wspace=0.22)
    axA, axB, axC, axD = (fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]),
                          fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1]))

    # ---- A 桥入存量 ----
    axA.plot(keep["date"], keep["bridged"] / 1e6, color=ORANGE, lw=1.5, zorder=3)
    axA.axvline(NATIVE_START, color=GREY, lw=1.0, ls=(0, (4, 3)), zorder=2)
    axA.annotate(f"峰值 {keep.loc[peak_i, 'bridged']/1e6:,.0f} 百万美元\n（{keep.loc[peak_i, 'date']:%Y-%m}）",
                 (keep.loc[peak_i, "date"], keep.loc[peak_i, "bridged"] / 1e6),
                 xytext=(8, -30), textcoords="offset points", ha="left", fontsize=9.8,
                 bbox=NOTE_BOX, zorder=6)
    axA.annotate(f"最新 {last['bridged']/1e6:,.1f} 百万美元\n（距峰值 {drop_peak:+.1f}%）",
                 (last["date"], last["bridged"] / 1e6),
                 xytext=(-8, 26), textcoords="offset points", ha="right", fontsize=9.8,
                 bbox=NOTE_BOX, zorder=6)
    axA.text(0.03, 0.13, f"灰虚线＝{NATIVE_START:%Y-%m-%d} Circle 在 Base 开始原生发行",
             transform=axA.transAxes, fontsize=9.4, color="#555555", bbox=NOTE_BOX, zorder=6)
    axA.set_ylim(0, 160)
    axA.set_ylabel("桥入存量（百万美元）")
    axA.set_title("桥入存量：峰值之后一路净流出", loc="left")
    year_axis(axA, first["date"], last["date"], f"{first['date']:%Y-%m}")

    # ---- B 桥入占流通量比例 ----
    axB.plot(keep["date"], keep["share"], color=BLUE, lw=1.8, zorder=3)
    axB.set_yscale("log")
    axB.set_ylim(0.1, 130)
    axB.set_yticks([0.1, 0.3, 1, 3, 10, 30, 100])
    axB.set_yticklabels(["0.1%", "0.3%", "1%", "3%", "10%", "30%", "100%"])
    axB.axvline(NATIVE_START, color=GREY, lw=1.0, ls=(0, (4, 3)), zorder=2)
    for d, lab, dy, ha in ((first["date"], f"起点 {first['share']:.0f}%（{first['date']:%Y-%m}）", -16, "left"),
                           (last["date"], f"最新 {last['share']:.2f}%（{last['date']:%Y-%m-%d}）", 16, "right")):
        s = keep.loc[keep["date"] == d, "share"].iloc[0]
        axB.annotate(lab, (d, s), xytext=(6 if ha == "left" else -8, dy), textcoords="offset points",
                     ha=ha, fontsize=9.8, bbox=NOTE_BOX, zorder=6)
    axB.set_ylabel("桥入占流通量比例（对数刻度）")
    axB.set_title("桥入占比：从全部到千分之一", loc="left")
    year_axis(axB, first["date"], last["date"], f"{first['date']:%Y-%m}")

    # ---- C 月度净变化 ----
    bars = mon["net"].dropna() / 1e6
    axC.bar(bars.index, bars.to_numpy(), width=20, color=[BLUE if v < 0 else ORANGE for v in bars],
            zorder=3)
    axC.axhline(0, color="#666666", lw=0.9, zorder=4)
    mx, mn = bars.idxmax(), bars.idxmin()
    axC.annotate(f"最大单月净流入 {bars[mx]:+,.1f}", (mx, bars[mx]), xytext=(8, 10),
                 textcoords="offset points", ha="left", fontsize=9.6, bbox=NOTE_BOX, zorder=6)
    axC.annotate(f"最大单月净流出 {bars[mn]:+,.1f}", (mn, bars[mn]), xytext=(0, -20),
                 textcoords="offset points", ha="center", fontsize=9.6, bbox=NOTE_BOX, zorder=6)
    axC.set_ylim(-45, 45)
    axC.set_ylabel("桥入存量月度净变化（百万美元）")
    axC.set_title(f"月度净变化：{neg_months}/{len(bars)} 个月净流出", loc="left")
    year_axis(axC, bars.index[0], bars.index[-1])

    # ---- D 口径陷阱 ----
    win = df[(df["date"] >= "2024-04-14") & (df["date"] <= "2024-04-25")]
    axD.plot(win["date"], win["bridged"] / 1e6, color=ORANGE, lw=1.8, marker="o", ms=3.4,
             zorder=4, label="桥入（含缺失日假值）")
    axD.plot(win["date"], win["bridged"].where(df["minted_usd"].notna()) / 1e6, color=ORANGE,
             lw=1.8, ls=(0, (4, 2)), zorder=5, label="桥入（剔除缺失日后）")
    axD.plot(win["date"], win["native"] / 1e6, color=BLUE, lw=1.6, zorder=3, label="原生发行")
    for d in bad:
        if win["date"].min() <= d <= win["date"].max():
            axD.axvline(d, color=GREY, lw=0.9, ls=(0, (2, 2)), zorder=2)
    b0 = bad.iloc[0] if len(bad) else None
    if b0 is not None:
        fake = float(df.loc[df["date"] == b0, "circulating_usd"].iloc[0] / 1e6)
        axD.annotate(f"{b0:%m-%d} minted 缺失：桥入被写成 {fake:,.0f} 百万美元\n"
                     f"（实际约 {last['bridged']/1e6:.0f} 百万美元量级）",
                     (b0, fake), xytext=(8, -18), textcoords="offset points", ha="left",
                     fontsize=9.4, bbox=NOTE_BOX, zorder=6)
    axD.set_ylim(0, 2700)
    axD.set_ylabel("百万美元")
    axD.set_title("口径陷阱：minted 缺失日会伪造桥入量", loc="left")
    dts = list(win["date"])
    axD.set_xticks(dts[::2])
    axD.set_xticklabels([f"{d:%m-%d}" for d in dts[::2]], fontsize=9.6)
    axD.set_xlim(win["date"].min() - pd.Timedelta(hours=8), win["date"].max() + pd.Timedelta(hours=8))
    axD.legend(loc="upper left", fontsize=9.0)
    axD.text(0.03, 0.45, f"2023-12-20 之后 minted 缺失 {len(bad)} 天；\n"
                         "本图其余统计一律按月度、剔除这些日子",
             transform=axD.transAxes, fontsize=9.4, color="#444444", va="top", bbox=NOTE_BOX, zorder=6)

    fig.suptitle("Base 链上 USDC：跨链桥通道的退场", x=0.075, ha="left",
                 fontsize=14.5, fontweight="bold", y=0.995)
    fig.text(0.075, 0.947,
             f"桥入存量 {first['bridged']/1e6:,.1f} 百万美元（{first['date']:%Y-%m}）→ "
             f"{last['bridged']/1e6:,.1f} 百万美元（{last['date']:%Y-%m-%d}），累计 {net_cum/1e6:+,.1f} 百万美元；"
             f"同期流通量净增 {circ_net/1e6:+,.0f} 百万美元，全部来自原生发行",
             fontsize=10.8, color="#333333")
    fig.text(0.075, 0.922,
             "上排：存量与占比（占比用对数刻度）｜ 下排：月度净变化，以及 minted 字段缺失如何伪造桥入量",
             fontsize=9.8, color="#666666")

    fig.text(0.075, 0.082,
             "数据来源：DefiLlama Stablecoins API（stablecoins.llama.fi/stablecoin/2 的 chainBalances.Base.tokens[]），"
             f"抓取于 {fetched}（UTC+8），本图不新增抓取。",
             fontsize=8.6, color="#444444")
    fig.text(0.075, 0.058,
             "口径：桥入存量 = 流通量 −（minted − unreleased），与 DefiLlama 的 bridgedTo 一致；"
             "月度为每月最后一个非缺失日，缺失日见右下角。",
             fontsize=8.6, color="#444444")
    fig.text(0.075, 0.034,
             "第三方聚合口径，未做链上逐笔核对；DefiLlama 的桥梁明细端点（bridges.llama.fi）2026-10-16 实测返回 HTTP 402，"
             "因此无法核对到具体是哪座桥。",
             fontsize=8.6, color="#444444")
    fig.subplots_adjust(left=0.075, right=0.975, top=0.872, bottom=0.15)

    for ext in ("png", "svg", "pdf"):
        fig.savefig(OUT / "figures" / f"base_usdc_bridge.{ext}", bbox_inches="tight")
    plt.close(fig)

    print(f"样本 {len(keep)} 行（原始 {len(df)} 行，剔除 minted 缺失 {len(bad)} 行："
          f"{', '.join(f'{d:%Y-%m-%d}' for d in bad)}）")
    print(f"桥入存量 {first['bridged']/1e6:,.2f}M（{first['date']:%Y-%m-%d}）→ 峰值 "
          f"{keep.loc[peak_i, 'bridged']/1e6:,.2f}M（{keep.loc[peak_i, 'date']:%Y-%m-%d}）→ "
          f"{last['bridged']/1e6:,.2f}M（{last['date']:%Y-%m-%d}）")
    print(f"桥入累计净变化 {net_cum/1e6:+,.1f}M；同期流通量净增 {circ_net/1e6:+,.0f}M；"
          f"原生净增 {(last['native'] - first['native'])/1e6:+,.0f}M")
    print(f"桥入占比 {first['share']:.2f}% → {last['share']:.2f}%；月度净流出 {neg_months}/{len(bars)} 个月")
    print(f"自检：原生 + 桥入 - 流通量 最大偏差 {err:.2e}；距峰值 {drop_peak:+.1f}%")
    print("已写出 figures/base_usdc_bridge.png（png/svg/pdf）")


if __name__ == "__main__":
    main()
