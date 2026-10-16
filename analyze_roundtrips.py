"""统计「同秒、等额、反向」的镜像往返，占一周样本金额的多大比例。

前置：先跑 fetch_transfers_week.py 生成 data/week/sample.csv（需要 441 MB 级
下载，因此 sample.csv 未入仓库；本脚本只读它，不读窗口文件）。

2026-10-16 实测：一周样本里金额 ≥ 100 万美元的 1,120 笔转账，全部能在样本内
找到同秒、等额、反向的另一笔，金额合计 267.9 亿美元，占该周样本总金额的
71.0%，参与地址只有 41 个；其中 0 笔是 from == to 的自转账，排除自匹配。
"""
import pandas as pd

SAMPLE = "data/week/sample.csv"
THRESHOLD = 1e6  # 只看百万美元以上的转账

w = pd.read_csv(SAMPLE)
big = w[w["usd"] >= THRESHOLD].copy()
tot = w["usd"].sum()

# 用 (秒级时间戳, 金额, from, to) 做键；反向键存在即视为镜像往返
keys = [(int(r[0]), round(r[1], 6), r[2], r[3]) for r in big[["timestamp", "usd", "from", "to"]].itertuples(index=False)]
pool = {(ts, usd, to, frm) for ts, usd, frm, to in keys}
mirror = [k for k in keys if (k[0], k[1], k[3], k[2]) in pool]

mv = sum(k[1] for k in mirror)
selfx = big[big["from"] == big["to"]]

print(f"一周样本共 {len(w):,} 笔、金额 {tot/1e9:.2f} 十亿美元")
print(f"金额 ≥ {THRESHOLD/1e6:.0f} 万美元的转账 {len(big):,} 笔、{big['usd'].sum()/1e9:.2f} 十亿美元"
      f"（占全部 {big['usd'].sum()/tot*100:.1f}%）")
print(f"其中能找到同秒、等额、反向另一笔的 {len(mirror):,} 笔、{mv/1e9:.2f} 十亿美元"
      f"（占全部 {mv/tot*100:.1f}%）")
print(f"参与地址 {len({k[2] for k in keys}):,} 个（from 计数）")
print(f"自查：大额里 from == to 的自转账 {len(selfx):,} 笔（会把自己误判成镜像）")

uniq = big.groupby("from")["usd"].sum().sort_values(ascending=False)
print("大额转出地址前 6（十亿美元）：")
for a, v in uniq.head(6).items():
    print(f"  {a}  {v/1e9:.2f}")
