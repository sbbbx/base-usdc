"""画第一张图：Base 链上 USDC 的流通量与市场份额（2023-08-16 – 2026-10-15）。

数据来源：data/usdc_base_daily.csv、data/base_stablecoins_daily.csv（由 fetch_data.py 抓取）。
口径：
  circulating（流通量）= minted（原生铸造）− unreleased（已铸造未释放）+ bridgedTo（跨链桥入）
  本图把流通量拆成「原生铸造」与「跨链桥入」两块，两者相加严格等于 circulating。
  share（份额）= USDC 在 Base 的流通量 ÷ Base 上所有锚定美元的稳定币流通量。

用法：python make_figure.py
产物：figures/base_usdc.png（网页用）、figures/base_usdc.svg（矢量，可再编辑）
"""

import json
import pathlib
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import MultipleLocator, StrMethodFormatter

ROOT = pathlib.Path(__file__).resolve().parent
FIG = ROOT / "figures"

C_NATIVE = "#2775CA"  # 原生铸造（USDC 品牌蓝）
C_BRIDGED = "#E8A33D"  # 跨链桥入
C_GRID = "#D8D8D8"

plt.rcParams.update(
    {
        "font.sans-serif": ["Microsoft YaHei", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 11,
        "axes.edgecolor": "#4D4D4D",
        "axes.labelcolor": "#1A1A1A",
        "text.color": "#1A1A1A",
        "xtick.color": "#4D4D4D",
        "ytick.color": "#4D4D4D",
    }
)

YI = 1e8  # 亿美元
# 标注落在面积图上时垫一层白底，避免深色文字压在蓝色填充上
NOTE_BOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=1.6)


def fetched_on() -> str:
    """抓取日期取自 data/meta.json，避免脚注写死。"""
    meta = json.loads((ROOT / "data" / "meta.json").read_text(encoding="utf-8"))
    return datetime.fromisoformat(meta["fetched_at_utc8"]).strftime("%Y-%m-%d")


def load() -> pd.DataFrame:
    usdc = pd.read_csv(ROOT / "data" / "usdc_base_daily.csv", parse_dates=["date"])
    chain = pd.read_csv(ROOT / "data" / "base_stablecoins_daily.csv", parse_dates=["date"])
    df = usdc.merge(chain, on="date", how="inner").set_index("date").sort_index()

    # 原生铸造 = minted − unreleased；早期没有 minted 字段（那时 Base 上 USDC 全部靠跨链桥入）
    df["native_usd"] = (df["minted_usd"].fillna(0) - df["unreleased_usd"].fillna(0)).clip(lower=0)
    df["bridged_usd"] = df["circulating_usd"] - df["native_usd"]
    df["share"] = df["circulating_usd"] / df["total_circulating_usd"]

    # 数据自检：两段之和必须回到 circulating，否则说明字段口径变了
    err = (df["native_usd"] + df["bridged_usd"] - df["circulating_usd"]).abs().max()
    assert err < 1.0, f"拆分与流通量对不上，最大误差 {err}"
    print(f"自检通过：拆分量与 circulating 的最大偏差 {err:.2e} USD，共 {len(df)} 个交易日点")
    return df


def draw(df: pd.DataFrame) -> plt.Figure:
    fig, (ax, ax2) = plt.subplots(
        2, 1, figsize=(11, 7.2), dpi=200, sharex=True,
        gridspec_kw={"height_ratios": [2.1, 1], "hspace": 0.12},
    )

    # ---- 上图：流通量，拆成原生铸造 + 跨链桥入 ----
    ax.stackplot(
        df.index,
        df["native_usd"] / YI,
        df["bridged_usd"] / YI,
        colors=[C_NATIVE, C_BRIDGED],
        labels=["原生铸造（Circle 直接发行）", "跨链桥入"],
        edgecolor="none",
    )
    ax.set_ylabel("Base 上 USDC 流通量（亿美元）")
    ax.set_ylim(0, 52)
    ax.yaxis.set_major_locator(MultipleLocator(10))
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:.0f}"))
    ax.grid(axis="y", color=C_GRID, lw=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=10.5, handlelength=1.4)

    peak_x = df["circulating_usd"].idxmax()
    last_x = df.index[-1]
    ax.annotate(
        f"峰值 {df.loc[peak_x, 'circulating_usd'] / YI:.1f} 亿（{peak_x:%Y-%m-%d}）",
        xy=(peak_x, df.loc[peak_x, "circulating_usd"] / YI),
        xytext=(-118, -34), textcoords="offset points", bbox=NOTE_BOX,
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.9),
        fontsize=10,
    )
    ax.annotate(
        f"最新 {df['circulating_usd'].iloc[-1] / YI:.1f} 亿",
        xy=(last_x, df["circulating_usd"].iloc[-1] / YI),
        xytext=(-96, 22), textcoords="offset points", bbox=NOTE_BOX,
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.9),
        fontsize=10,
    )
    ax.annotate(
        f"起点 {df['circulating_usd'].iloc[0] / YI:.1f} 亿",
        xy=(df.index[0], df["circulating_usd"].iloc[0] / YI),
        xytext=(6, 26), textcoords="offset points", bbox=NOTE_BOX,
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.9),
        fontsize=10,
    )

    # ---- 下图：USDC 在 Base 美元稳定币中的份额 ----
    ax2.plot(df.index, df["share"] * 100, color=C_NATIVE, lw=1.6)
    ax2.fill_between(df.index, 70, df["share"] * 100, color=C_NATIVE, alpha=0.12, lw=0)
    ax2.set_ylabel("USDC 份额（%）")
    ax2.set_ylim(70, 100)
    ax2.yaxis.set_major_locator(MultipleLocator(10))
    ax2.grid(axis="y", color=C_GRID, lw=0.8)
    ax2.set_axisbelow(True)
    for side in ("top", "right"):
        ax2.spines[side].set_visible(False)

    share_peak_x = df.loc["2024-04":, "share"].idxmax()
    ax2.annotate(
        f"高点 {df.loc[share_peak_x, 'share'] * 100:.0f}%（{share_peak_x:%Y-%m-%d}）",
        xy=(share_peak_x, df.loc[share_peak_x, "share"] * 100),
        xytext=(-150, -6), textcoords="offset points", bbox=NOTE_BOX,
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.9),
        fontsize=10,
    )
    ax2.annotate(
        f"最新 {df['share'].iloc[-1] * 100:.1f}%",
        xy=(last_x, df["share"].iloc[-1] * 100),
        xytext=(-84, 14), textcoords="offset points", bbox=NOTE_BOX,
        arrowprops=dict(arrowstyle="-", color="#666666", lw=0.9),
        fontsize=10,
    )

    # ---- 横轴与标题 ----
    # 首点单独打一个「年-月」刻度，否则 2023 那一段没有年份标签
    start_x = df.index[0]
    year_ticks = [pd.Timestamp(f"{y}-01-01") for y in range(start_x.year + 1, last_x.year + 1)]
    ax2.set_xticks([start_x] + year_ticks)
    ax2.set_xticklabels([f"{start_x:%Y-%m}"] + [f"{t:%Y}" for t in year_ticks])
    ax2.xaxis.set_minor_locator(mdates.MonthLocator(bymonth=[4, 7, 10]))
    ax2.set_xlabel("时间（UTC 日度数据）")
    ax2.set_xlim(start_x, last_x)

    fig.suptitle("Base 链上 USDC：流通量与市场份额", x=0.09, y=0.975, ha="left",
                 fontsize=15, fontweight="bold")

    fig.text(
        0.09, 0.018,
        f"数据来源：DefiLlama Stablecoins API（stablecoins.llama.fi），抓取于 {fetched_on()}（UTC+8）。\n"
        "口径：流通量 = 原生铸造 − 未释放 + 跨链桥入；份额分母为 Base 上锚定美元的稳定币流通总量。",
        fontsize=8.5, color="#595959", va="bottom", linespacing=1.5,
    )
    return fig


def main() -> None:
    FIG.mkdir(exist_ok=True)
    df = load()
    fig = draw(df)
    fig.subplots_adjust(left=0.09, right=0.97, top=0.9, bottom=0.188)
    png = FIG / "base_usdc.png"
    fig.savefig(png, facecolor="white")
    fig.savefig(FIG / "base_usdc.svg", facecolor="white")
    fig.savefig(FIG / "base_usdc.pdf", facecolor="white")
    print(f"已输出 {png}（含 .svg / .pdf）")


if __name__ == "__main__":
    main()
