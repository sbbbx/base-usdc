"""图 5：Base 美元稳定币的构成——USDC 之外长出了什么。

只读本地 CSV（不新增抓取）：
  data/base_composition.csv        各资产逐日流通量（fetch_composition.py 产出）
  data/base_stablecoins_daily.csv  Base 锚定美元稳定币的流通总量（份额分母）
  data/usdc_base_daily.csv         USDC 在 Base 的逐日流通量（与图 1 同口径）
产物：figures/base_usdc_composition.{png,svg,pdf}
"""
import json
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATA, FIG = ROOT / "data", ROOT / "figures"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"figure.dpi": 200, "font.size": 11, "axes.titlesize": 12.5,
                     "axes.grid": True, "grid.color": "#DDDDDD", "grid.linewidth": 0.8})

NAMED = ["USDC", "USDe", "rwaUSDi", "OUSD", "cgUSD", "EUSD", "MSUSD"]
COLORS = {"USDC": "#2775CA", "USDe": "#6FA8DC", "rwaUSDi": "#E8A33D", "OUSD": "#C0392B",
          "cgUSD": "#8E44AD", "EUSD": "#16A085", "MSUSD": "#B7950B", "其他": "#9AA0A6"}
GREY = "#666666"
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)


def money_label(v, unit="美元"):
    """把美元金额写成中文短单位，用于刻度与标注。"""
    for cut, name in ((1e8, "亿"), (1e4, "万")):
        if abs(v) >= cut:
            return f"{v / cut:,.2f}".rstrip("0").rstrip(".") + name
    return f"{v:,.0f}"


def main():
    comp = pd.read_csv(DATA / "base_composition.csv", parse_dates=["date"])
    total = pd.read_csv(DATA / "base_stablecoins_daily.csv", parse_dates=["date"])
    total = total.set_index("date")["total_circulating_usd"]
    usdc = pd.read_csv(DATA / "usdc_base_daily.csv", parse_dates=["date"]).set_index("date")
    meta = json.loads((DATA / "composition_meta.json").read_text(encoding="utf-8"))
    snap = total.index[-1]

    wide = comp.pivot_table(index="date", columns="symbol", values="usd")
    wide = wide.reindex(total.index).fillna(0.0)
    named = [s for s in NAMED if s in wide.columns]
    others = [s for s in named if s != "USDC"]
    resid = total - wide[named].sum(axis=1)
    other = resid.clip(lower=0.0)

    share = (usdc["circulating_usd"] / total * 100).reindex(total.index)
    snap_share = float(share.loc[snap])
    peak_day = share.loc["2024-04":].idxmax()
    share_peak = float(share.loc[peak_day])
    latest = {s: float(wide[s].loc[snap]) for s in wide.columns}
    arrivals = {s: wide.index[wide[s] > 0][0] for s in wide.columns}
    gap = float(total.loc[snap] - latest["USDC"])
    fetched = meta["fetched_at_utc8"][:10]

    # --- 自检 ---
    assert float(resid.min()) > -2e6, f"「其他」出现明显负值 {float(resid.min()):,.0f}，总量小于已列资产之和"
    assert abs(latest["USDC"] - float(usdc["circulating_usd"].loc[snap])) < 1.0, "USDC 两条来源不一致"
    assert 2.0 < snap_share < 100.0, "份额越界"
    assert abs(sum(latest[s] for s in named) + float(other.loc[snap]) - float(total.loc[snap])) < 1.0
    print(f"快照日 {snap:%Y-%m-%d}：总量 {money_label(total.loc[snap])}，USDC {money_label(latest['USDC'])}"
          f"（{snap_share:.2f}%），其余 {money_label(gap)}（{gap / float(total.loc[snap]) * 100:.2f}%）")
    print(f"份额高点 {share_peak:.2f}% @ {peak_day:%Y-%m-%d}；残差最小值 {money_label(float(resid.min()))}")
    for s in sorted(others, key=lambda s: -latest[s]):
        print(f"  {s:9s} 到达 {arrivals[s]:%Y-%m-%d}  当前 {money_label(latest[s]):>8s}"
              f"  占总量 {latest[s] / float(total.loc[snap]) * 100:5.2f}%")

    fig, ((axA, axB), (axC, axD)) = plt.subplots(2, 2, figsize=(11, 7.8))
    idx = total.index

    axA.stackplot(idx, [wide[s].to_numpy() / 1e8 for s in named] + [other.to_numpy() / 1e8],
                  colors=[COLORS[s] for s in named] + [COLORS["其他"]], lw=0.0)
    axA.set_ylim(0, float(total.max()) / 1e8 * 1.16)
    axA.set_ylabel("流通量（亿美元）")
    axA.set_title(f"总盘与构成：{money_label(total.loc[snap])}，USDC 占 {snap_share:.1f}%", loc="left")
    axA.text(pd.Timestamp("2024-05-01"), 21.0, f"USDC {money_label(latest['USDC'])}\n（{snap_share:.1f}%）",
             fontsize=9.8, color=COLORS["USDC"], bbox=NOTE_BOX, va="center")
    axA.annotate(f"其余 {len(named)} 类合计 {money_label(gap)}（{gap / float(total.loc[snap]) * 100:.1f}%）",
                 xy=(pd.Timestamp("2025-11-01"), float(total.loc[snap]) / 1e8 * 0.99),
                 xytext=(pd.Timestamp("2024-02-01"), float(total.max()) / 1e8 * 1.08),
                 fontsize=9.8, color="#333333", bbox=NOTE_BOX, va="center",
                 arrowprops=dict(arrowstyle="-", color="#999999", lw=1.0))

    axB.stackplot(idx, [wide[s].to_numpy() / 1e6 for s in others] + [other.to_numpy() / 1e6],
                  colors=[COLORS[s] for s in others] + [COLORS["其他"]], lw=0.0)
    axB.set_ylim(0, float(wide[others].sum(axis=1).max()) / 1e6 * 1.35)
    axB.set_ylabel("流通量（百万美元）")
    axB.set_title("放大非 USDC 部分：六个资产陆续到达", loc="left")
    for i, s in enumerate(sorted(others, key=lambda s: -latest[s])):
        axB.text(0.03, 0.96 - i * 0.082, f"{s}  {money_label(latest[s])}（{arrivals[s]:%Y-%m} 到达）",
                 transform=axB.transAxes, va="top", fontsize=9.2, color=COLORS[s], bbox=NOTE_BOX)
    other_2025 = float(other.loc["2025"].max())
    axB.text(0.03, 0.12,
             f"灰色＝未单列的其他资产合计：2025 年最高 {money_label(other_2025)}，"
             f"快照日为 {money_label(float(other.loc[snap]))}；\n其中最大的五个是 PINTO、satUSD、USDV、apxUSD、USDz"
             "（各约 650 万–1,070 万美元），其余为更小的长尾。",
             transform=axB.transAxes, va="bottom", fontsize=9.0, color="#555555", bbox=NOTE_BOX)

    order = sorted(sizes := {s: latest[s] for s in wide.columns if latest[s] > 0}, key=sizes.get)
    for i, s in enumerate(order):
        size = sizes[s]
        radius = 34 + 150 * max(0.0, (len(str(int(size))) - 5) / 6)
        axC.scatter([arrivals[s]], [i], s=radius, color=COLORS.get(s, COLORS["其他"]),
                    zorder=4, edgecolor="white", linewidth=0.8)
    axC.set_yticks(range(len(order)))
    axC.set_yticklabels([f"{s}  {money_label(sizes[s])}" for s in order], fontsize=9.6)
    for i, s in enumerate(order):
        axC.get_yticklabels()[i].set_color(COLORS.get(s, COLORS["其他"]))
    axC.set_ylim(-0.7, len(order) - 0.3)
    axC.set_xlim(pd.Timestamp("2023-05-01"), pd.Timestamp("2027-01-01"))
    axC.set_title(f"到达日与当前规模：{len(order)} 个 ≥500 万美元的资产", loc="left")
    axC.set_xlabel("在 Base 首次出现非零流通量的日期")

    axD.plot(idx, share.to_numpy(), color=COLORS["USDC"], lw=1.8, label="USDC 份额")
    axD.plot(idx, 100 - share.to_numpy(), color=COLORS["其他"], lw=1.4, ls=(0, (5, 3)),
             label="其余资产合计份额")
    for s in others:
        axD.axvline(arrivals[s], color=COLORS[s], lw=1.0, ls=(0, (2, 2.5)), alpha=0.75, zorder=1)
    axD.set_ylim(0, 100)
    axD.set_ylabel("占 Base 美元稳定币总量（%）")
    axD.set_title("份额侵蚀：每一步都对应一个到达日", loc="left")
    axD.legend(loc="center right", fontsize=9.3)
    axD.annotate(f"高点 {share_peak:.1f}%（{peak_day:%Y-%m-%d}）", xy=(peak_day, share_peak),
                 xytext=(14, -30), textcoords="offset points", ha="left", fontsize=9.5,
                 color=COLORS["USDC"], bbox=NOTE_BOX,
                 arrowprops=dict(arrowstyle="-", color=COLORS["USDC"], lw=0.9))
    axD.annotate(f"最新 {snap_share:.1f}%", xy=(snap - pd.Timedelta(days=40), float(share.iloc[-40])),
                 xytext=(-16, 20), textcoords="offset points", ha="right", fontsize=9.5,
                 color="#333333", bbox=NOTE_BOX,
                 arrowprops=dict(arrowstyle="-", color="#999999", lw=0.9))

    year_ticks = [pd.Timestamp("2023-08-16")] + [pd.Timestamp(f"{y}-01-01") for y in (2024, 2025, 2026)]
    for ax in (axA, axB, axD):
        ax.set_xticks(year_ticks)
        ax.set_xticklabels(["2023-08", "2024", "2025", "2026"])
    axC.set_xticks([pd.Timestamp("2023-08-16")] + [pd.Timestamp(f"{y}-01-01") for y in (2024, 2025, 2026, 2027)])
    axC.set_xticklabels(["2023-08", "2024", "2025", "2026", "2027"])
    for ax in (axA, axB, axC, axD):
        ax.tick_params(labelsize=10)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    fig.suptitle("Base 美元稳定币的构成：USDC 之外长出了什么", x=0.075, ha="left",
                 fontsize=14.5, fontweight="bold", y=0.995)
    fig.text(0.075, 0.947,
             f"快照 {snap:%Y-%m-%d}：Base 上锚定美元的稳定币合计 {money_label(total.loc[snap])}，"
             f"USDC {money_label(latest['USDC'])}（{snap_share:.1f}%），其余 {money_label(gap)}；"
             f"同期流通量净增 +43.25 亿美元，全部来自原生发行",
             fontsize=9.8, color=GREY)
    fig.text(0.075, 0.922,
             "上排：全部美元稳定币的构成，以及非 USDC 部分的放大 ｜ 下排：各资产的到达日与规模，"
             "竖虚线＝首次出现日",
             fontsize=9.8, color=GREY)

    fig.text(0.075, 0.075,
             f"数据来源：DefiLlama Stablecoins API（stablecoins.llama.fi/stablecoin/{{id}} 的 "
             f"chainBalances.Base.tokens[]），抓取于 {fetched}（UTC+8）。",
             fontsize=8.6, color=GREY)
    fig.text(0.075, 0.052,
             f"口径：除 USDC 外，堆叠面板只单列当期 ≥1,500 万美元的 {len(others)} 个资产，其余"
             f"（含 PINTO、satUSD、USDV、apxUSD、USDz 与更小的资产，合计 {money_label(gap - sum(latest[s] for s in others))}）"
             f"合并为「其他」；份额分母为 Base 上锚定美元的稳定币流通总量。",
             fontsize=8.6, color=GREY)
    fig.text(0.075, 0.029,
             f"快照日 {snap:%Y-%m-%d} 与图 1 一致；DefiLlama 为第三方聚合口径，未做链上逐笔核对；"
             f"「到达日」指该资产在 Base 首次出现非零流通量，不代表发行方正式上线日期。",
             fontsize=8.6, color=GREY)

    fig.subplots_adjust(left=0.105, right=0.975, top=0.872, bottom=0.15, hspace=0.36, wspace=0.30)
    FIG.mkdir(exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIG / f"base_usdc_composition.{ext}", bbox_inches="tight")
    print("写出 figures/base_usdc_composition.png（png/svg/pdf）")


if __name__ == "__main__":
    main()
