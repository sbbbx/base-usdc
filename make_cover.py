"""拼一张投稿用封面：五张图 + 一个文字块，输出 2:1 横版（GitHub social preview 与投稿封面通用）。

只读 figures/ 下已生成的 PNG，不重算任何数据。文字全用英文（面向海外渠道），
并设 CJK 兜底字体以防未来混入中文。用法：python -u make_cover.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

plt.rcParams["font.family"] = ["Microsoft YaHei", "DejaVu Sans"]

FIG = [
    ("base_usdc.png", "Fig 1 · Stock and share"),
    ("base_usdc_transfers.png", "Fig 2 · 24-hour transfer slice"),
    ("base_usdc_week.png", "Fig 3 · One-week baseline"),
    ("base_usdc_bridge.png", "Fig 4 · Bridge channel exit"),
    ("base_usdc_composition.png", "Fig 5 · What grew beside USDC"),
]
BLUE, ORANGE, GREY = "#2775CA", "#E8A33D", "#666666"
OUT = "figures/base_usdc_cover.png"

fig = plt.figure(figsize=(12, 6), dpi=200, facecolor="white")
fig.subplots_adjust(left=0.012, right=0.988, top=0.965, bottom=0.012, wspace=0.04, hspace=0.10)

for i, (fname, caption) in enumerate(FIG):
    ax = fig.add_subplot(2, 3, i + 1)
    ax.imshow(mpimg.imread(f"figures/{fname}"))
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_color("#CCCCCC")
        s.set_linewidth(0.8)
    ax.set_title(caption, fontsize=9.6, color=GREY, pad=3.5)

ax = fig.add_subplot(2, 3, 6)
ax.axis("off")
ax.add_patch(Rectangle((0.02, 0.02), 0.96, 0.96, transform=ax.transAxes,
                       facecolor="#F7F9FC", edgecolor="#D6DEE8", linewidth=1.0))
ax.text(0.07, 0.90, "USDC on Base", transform=ax.transAxes, fontsize=15,
        fontweight="bold", color="#111111")
ax.text(0.07, 0.80, "Benjamin Shen", transform=ax.transAxes, fontsize=9.6, color=GREY)
ax.text(0.07, 0.68, "$4.38B of stock · 84.4% of the dollar supply\n$7.06B moved in a 24-hour block sample",
        transform=ax.transAxes, fontsize=11, color=BLUE, linespacing=1.5)
ax.text(0.07, 0.34,
        "Stock, share, a 24-hour transfer slice, a one-week\n"
        "baseline, the bridge channel's exit, and what grew\n"
        "beside USDC.\n"
        "5 figures · 6 scripts · bilingual write-up",
        transform=ax.transAxes, fontsize=8.8, color="#333333", linespacing=1.6)
ax.text(0.07, 0.24, "github.com/sbbbx/base-usdc", transform=ax.transAxes,
        fontsize=10.5, color=ORANGE, fontweight="bold")
ax.text(0.07, 0.10,
        "DefiLlama Stablecoins API + public Base RPC (no API key)\n"
        "Fetched 2026-10-15 / 10-16 · caveats in each figure",
        transform=ax.transAxes, fontsize=7.8, color=GREY, linespacing=1.5)

fig.savefig(OUT)
fig.savefig(OUT.replace(".png", ".pdf"))
print(f"写出 {OUT}（png/pdf）")
