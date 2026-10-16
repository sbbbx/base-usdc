"""图 6：USDC 转账的地址图景——按笔与按地址两套集中度、地址活跃度、往返成分、前 10 名地址。

只读本地文件（不联网）：
  data/week/sample.csv        168 个 50 区块窗口的 USDC Transfer 日志（图 3 同一样本）
  data/address_stats.json     analyze_addresses.py 的聚合结果
  data/address_curve.csv      集中度曲线的采样点（rank 与累计占比）
  data/address_evidence.json  闪电贷同笔交易的链上核验记录
产物：figures/base_usdc_addresses.{png,svg,pdf}
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

BLUE, ORANGE, GREY, DARK = "#2775CA", "#E8A33D", "#666666", "#C0392B"
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)


def money_label(v, unit="美元"):
    """把美元金额写成中文短单位，用于刻度与标注。"""
    for cut, name in ((1e8, "亿"), (1e4, "万")):
        if abs(v) >= cut:
            return f"{v / cut:,.2f}".rstrip("0").rstrip(".") + name
    return f"{v:,.0f}"


def short(addr, n=10):
    return f"{addr[:n]}…"


def main():
    s = json.loads((DATA / "address_stats.json").read_text(encoding="utf-8"))
    ev = json.loads((DATA / "address_evidence.json").read_text(encoding="utf-8"))
    cur = pd.read_csv(DATA / "address_curve.csv")

    smp, pa, pt, ch, net = s["sample"], s["by_address"], s["by_transfer"], s["churn"], s["net"]
    gross, part = smp["usd_total"], pa["part_total"]
    logs, addrs = smp["logs"], smp["unique_addresses"]
    top = {float(k.replace("pct", "")): v for k, v in pa["top"].items() if not k.startswith("top_")}

    def curve(basis, kind):
        d = cur[(cur.basis == basis) & (cur.kind == kind)].sort_values("rank_or_frac")
        return d["rank_or_frac"].to_numpy(), d["cum_share"].to_numpy()

    fig, ((axA, axB), (axC, axD)) = plt.subplots(2, 2, figsize=(11, 8.0))

    # A：两套集中度曲线（横轴＝排名，对数刻度）
    a_rank, a_cum = curve("address", "log_rank")
    t_rank, t_cum = curve("transfer", "log_rank")
    t_frac, t_lin = curve("transfer", "lin")
    t1 = float(t_lin[(abs(t_frac - 0.01)).argmin()])
    axA.plot(a_rank, a_cum * 100, color=BLUE, lw=2.3, label=f"按地址的参与额（{addrs:,} 个）")
    axA.plot(t_rank, t_cum * 100, color=ORANGE, lw=2.0, label=f"按单笔转账金额（{logs:,} 笔）")
    axA.set_xscale("log")
    axA.set_xlim(1, 1e6)
    axA.set_ylim(0, 100)
    axA.set_xlabel("排名（对数刻度）")
    axA.set_ylabel("累计占比（%）")
    axA.annotate(f"前 10 名地址：{top[10]:.1%}", xy=(10, top[10] * 100), xytext=(26, 58),
                 fontsize=9, color=BLUE, bbox=NOTE_BOX,
                 arrowprops=dict(arrowstyle="-", color=BLUE, lw=1.0))
    axA.annotate(f"前 100 名地址：{top[100]:.1%}", xy=(100, top[100] * 100), xytext=(1.6e3, 74),
                 fontsize=9, color=BLUE, bbox=NOTE_BOX,
                 arrowprops=dict(arrowstyle="-", color=BLUE, lw=1.0))
    axA.annotate(f"前 1% 的笔：{t1:.1%}", xy=(logs * 0.01, t1 * 100),
                 xytext=(3, 12), fontsize=9, color=ORANGE, bbox=NOTE_BOX,
                 arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1.0))
    axA.set_title(f"A 两套集中度（蓝＝按地址、橙＝按笔）：地址中位数 {money_label(pa['median_usd'])}，"
                  f"单笔中位数 {money_label(pt['median_usd'])}", loc="left", fontsize=11.5)

    # B：地址活跃度分档（两条线不填面，避免柱状图相互遮挡）
    b = pd.DataFrame(pa["buckets"])
    xb = list(range(len(b)))
    axB.plot(xb, b["addr_share"] * 100, "-o", color=BLUE, lw=2.0, ms=6, label="占地址数")
    axB.plot(xb, b["usd_share"] * 100, "-s", color=ORANGE, lw=2.0, ms=6, label="占参与额")
    axB.set_yscale("log")
    axB.set_ylim(0.04, 220)
    axB.set_xlim(-0.22, len(b) - 0.28)
    axB.set_xticks(xb)
    axB.set_xticklabels(b["label"], fontsize=9.5)
    axB.set_xlabel("该地址在这个样本里参与了几笔", labelpad=2)
    axB.set_ylabel("占比（%，对数刻度）")
    axB.legend(loc="upper left", bbox_to_anchor=(0.015, 0.995), ncol=2, fontsize=9, frameon=False)
    for i, r in b.iterrows():
        axB.text(i + 0.09, r["addr_share"] * 100, f"{r['addr_share']:.2%}", ha="left", va="center",
                 fontsize=8.6, color=BLUE)
        axB.text(i + 0.09, r["usd_share"] * 100, f"{r['usd_share']:.2%}", ha="left", va="center",
                 fontsize=8.6, color=ORANGE)
    first, last = b.iloc[0], b.iloc[-1]
    axB.set_title(f"B 谁在动钱：{first['addr_share']:.1%} 的地址只出现 1 笔（占金额 "
                  f"{first['usd_share']:.2%}），{last['addresses']:.0f} 个地址占了 {last['usd_share']:.1%}",
                  loc="left", fontsize=11.5)

    # C：毛额里有多少是「来回」
    rows = [("双向对：同一对地址\n来回都转过", ch["both_share"], BLUE),
            ("同窗口：100 秒内\n出现反向转账", ch["window_rev_share"], BLUE),
            ("同区块：同一秒内\n原路返回", ch["block_rev_share"], ORANGE),
            ("净流入最大 + 净流出\n最大的两个地址之和", (net["max_in"] + net["max_out"]) / gross, GREY)]
    ypos = range(len(rows))
    axC.barh(list(ypos), [r[1] * 100 for r in rows], color=[r[2] for r in rows], height=0.62)
    axC.set_yticks(list(ypos))
    axC.set_yticklabels([r[0] for r in rows], fontsize=9.5)
    axC.invert_yaxis()
    axC.set_xlim(0, 62)
    axC.set_xlabel(f"占样本转账总额（{money_label(gross)}）的比例（%）")
    for i, r in enumerate(rows):
        axC.text(r[1] * 100 + 1.2, i, f"{r[1]:.2%}", va="center", fontsize=9.5, color=r[2])
    axC.set_title("C 一半以上的金额在往返：50 区块窗口内 48.8%、同一秒内 45.4%", loc="left", fontsize=11.5)
    axC.text(0.20, 0.015, 
             "最大的一笔往返：同一笔交易里借出\n并还回 2.39 亿美元，进出完全相等",
             transform=axC.transAxes, va="bottom", ha="left", fontsize=8.5, color=DARK, linespacing=1.55,
             bbox=dict(facecolor="#FDF3E7", edgecolor=ORANGE, lw=0.8, pad=3.5))

    # D：前 10 名地址的参与额与净额
    t10 = pd.DataFrame(s["top_addresses"]).head(10).iloc[::-1]
    ypos = range(len(t10))
    axD.barh(list(ypos), t10["share"] * 100, color=BLUE, height=0.62)
    axD.set_yticks(list(ypos))
    axD.set_yticklabels([short(a) for a in t10["address"]], fontsize=9)
    axD.set_xlim(0, 58)
    axD.set_xlabel(f"占地址参与额（{money_label(part)}）的比例（%）")
    for i, r in enumerate(t10.itertuples()):
        sign = "＋" if r.net >= 0 else "−"
        axD.text(r.share * 100 + 1.0, i, f"{r.share:.1%}　{r.n:,} 笔　净额 {sign}{money_label(abs(r.net))}",
                 va="center", fontsize=8.6, color=GREY)
    axD.set_title(f"D 前 10 名占了 {top[10]:.1%}，但进≈出：它们不是持有者，是通道", loc="left", fontsize=11.5)

    fig.suptitle("USDC 在 Base 上的转账：钱在少数通道里打转，不在多数地址手里停留", x=0.075, ha="left",
                 fontsize=14.5, fontweight="bold", y=0.995)
    fig.text(0.075, 0.947,
             f"一周采样 {smp['windows']} 个 50 区块窗口（共 8,400 区块 ≈ 该周的 2.8%）：{logs:,} 条日志、"
             f"毛额 {money_label(gross)}、{addrs:,} 个地址；其中 {ch['block_rev_share']:.1%} 的金额在同一秒里原路返回，"
             f"净流出最大的地址也只挪走 {money_label(net['max_out'])}",
             fontsize=9.8, color=GREY)
    fig.text(0.075, 0.922,
             "上排：按地址与按笔两套集中度曲线、地址活跃度分档 ｜ 下排：往返成分、前 10 名地址的参与额与净额",
             fontsize=9.8, color=GREY)

    fig.text(0.075, 0.083,
             "数据来源：data/week/sample.csv（eth_getLogs 抓取 USDC Transfer 事件，与图 3 同一样本，"
             "抓取于 2026-10-15/16）；聚合见 analyze_addresses.py，闪电贷核验见 data/address_evidence.json。",
             fontsize=8.6, color=GREY)
    fig.text(0.075, 0.060,
             f"口径：地址集中度用「参与额」＝每笔转账在收方与发方各计一次（合计 {money_label(part)}）；单笔集中度用转账原始金额；"
             "往返三口径：双向对＝同一对地址在本周双向都有转账，同窗口＝同一 50 区块窗口内出现反向转账，同区块＝同一区块内出现反向转账；"
             "mint/burn（2,673 万 / 1,781 万美元）不计入地址参与额与往返口径。",
             fontsize=8.6, color=GREY)
    fig.text(0.075, 0.037,
             f"核验：块 {ev['block']:,} 的 {ev['chain_logs']} 条链上日志与本地样本逐条一致，其中 tx {ev['witness_tx'][:10]}… 在同一笔交易内"
             f"借出并归还 {ev['witness_legs'][0][2]:,.2f} USDC（进出相等，闪电贷特征）；前 15 名的净额都不足其参与额的 0.05%；"
             "地址标签（0xbbbb…＝Morpho Blue 借贷合约）来自公开浏览器标注，非项目方确认。",
             fontsize=8.6, color=GREY)

    fig.subplots_adjust(left=0.125, right=0.975, top=0.872, bottom=0.175, hspace=0.62, wspace=0.34)
    FIG.mkdir(exist_ok=True)
    for ext in ("png", "svg", "pdf"):
        fig.savefig(FIG / f"base_usdc_addresses.{ext}", bbox_inches="tight")
    print("写出 figures/base_usdc_addresses.png（png/svg/pdf）")


if __name__ == "__main__":
    main()
