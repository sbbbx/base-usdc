# 投稿材料包 · USDC on Base

面向链上数据悬赏渠道的投放素材。**一句话结论**与**短摘要**可直接粘贴到投稿表单，长摘要用于论坛/Issue 正文。
素材只包含仓库里已经公开、可复算的东西；所有数字都能在仓库中找到对应图与脚本。

- 仓库：https://github.com/sbbbx/base-usdc （MIT，tag v0.5）
- 封面图：[`figures/base_usdc_cover.png`](../figures/base_usdc_cover.png)
- 技术文：[`article.md`](../article.md)（中文）· [`article.en.md`](../article.en.md)（English）
- 作者署名：Benjamin Shen（github.com/sbbbx）

---

## 1. 一句话结论（表单用）

**EN**：I analysed USDC on Base using free, keyless public endpoints only: 3.5 years of stock and share, a 24-hour transfer sample, a one-week baseline, the bridge channel's exit, what grew beside USDC, and who actually moves it — by address, not only by transfer.

**ZH**：只用免费免 key 的公开接口，把 Base 上 USDC 的存量与份额、24 小时逐笔转账采样、一周基线、跨链桥通道的退场、「USDC 之外长出了什么」与「钱在哪些地址手里」，做成了六张可复现的图。

（英文 256 字符；中文 100 字）

## 2. 短摘要（约 430 字）

**ZH**：数据全部来自两个免 key 接口：DefiLlama 稳定币 API 与 Base 公共 RPC。存量侧用日度序列，转账侧用 `eth_getLogs` 按小时抽一个 50 区块窗口（覆盖该周区块的 2.78%），脚本用标准库加 pandas 本地计算。结论是：Base 上 USDC 的规模增长完全由 Circle 原生发行承担，跨链桥入从唯一入口退到 0.14% 的零头；转账笔数有稳定的日内节律，但金额高度集中，且单日采样会把「集中度」估高——一周基线里前 1% 的转账承担 80.5% 的金额，其中百万美元以上的 1,120 笔全部能在同一秒找到等额反向的另一笔，属净额为零的搬运。把同一份样本换成地址口径看，集中度更极端：前 10 个地址就占 87.3% 的参与额，62.7% 的地址只出现 1 笔（合计只占 0.09% 的金额），45.4% 的金额在同一区块内原路返回，前 15 名地址的净额都不足自身参与额的 0.05%——它们是通道，不是持有者。

## 3. Long abstract (EN, ~230 words)

I looked at USDC on Base with nothing but free, keyless endpoints: DefiLlama's stablecoin API for daily stock and per-asset series, and public Base RPC endpoints for raw `Transfer` logs. Six figures came out of it, and each states its own sampling method.

Stock: USDC on Base went from $52.8M (2023-08-16) to $4.38B (2026-10-15), peaking at $4.77B (2026-01-22), and 99.86% of it is now minted natively rather than bridged. Share of Base's dollar stablecoins is 84.4%, down from a 97.2% high (2024-04-23) — not because USDC shrank but because the denominator grew: USDe, rwaUSDi, OUSD, cgUSD and others arrived one by one.

Flows: in 93,656 logs sampled over 24 hours, USDC averaged 2,387 transfers per minute, median size $96, with the top 1% of transfers carrying 92.6% of the value. A one-week baseline (730,778 logs, 168 hourly windows, 2.78% of that week's blocks) puts the median at $93 — robust — but the concentration at 80.5%, because that metric is decided by a few very large transfers. Of the 1,120 transfers ≥$1M in the week sample, every single one pairs with a same-second, equal-amount transfer in the opposite direction, from 41 distinct addresses: the largest USDC flows on Base are round trips, not net settlement.

Addresses: the same week sample counted by address instead of by transfer is more concentrated still. The top 10 addresses carry 87.3% of participation (top 100: 99.0%), the Gini coefficient is 0.9998, and 62.7% of the 135,779 addresses appear exactly once — for 0.09% of the value. 45.4% of the value never leaves the second it arrived in, and the largest net inflow anywhere in the sample is $15.0M. The top ten are channels, not holders: the largest, tagged by a public explorer as the Morpho Blue lending contract, accounts for 33.7% of participation and nets out to under 0.02% of it. One on-chain check anchors the claim: in block 52,650,046 a single transaction borrows $238,890,119.82 from that contract and repays it inside the same transaction — the signature of a zero-fee flash loan — and the block's 93 logs match the local sample row by row.

## 4. 关键数字（投稿时可引用的锚点）

| 指标 | 值 | 出处 |
| --- | --- | --- |
| 存量（2026-10-15） | 43.78 亿美元 | 图 1 / `data/usdc_base_daily.csv` |
| 起点（2023-08-16） | 0.528 亿美元（≈83 倍） | 图 1 |
| 峰值 | 47.72 亿美元（2026-01-22，−8.3%） | 图 1 |
| 原生占比 | 99.86%（原生 43.72 亿 / 桥入 632 万） | 图 1、图 4 |
| 份额 | 84.4%（高点 97.2% @ 2024-04-23） | 图 1、图 5 |
| 桥入存量 | 632 万美元，较 2023-09-04 峰值 −94.9%，26/38 个月净流出 | 图 4 |
| 24 小时采样 | 93,656 条日志 / 2,387 笔每分钟 / 中位数 96 美元 / 前 1% 占 92.6% | 图 2 |
| 一周基线 | 730,778 条日志 / 168 窗口 / 中位数 93 美元 / 前 1% 占 80.5% | 图 3 |
| 大额搬运 | ≥100 万美元的 1,120 笔（占金额 71.0%）全部同秒反向配对，来自 41 个地址 | 图 3、`analyze_roundtrips.py` |
| 地址集中度 | 前 10 名占参与额 87.3%、前 100 名 99.0%（按笔口径为前 1% 占 80.5%）；基尼 0.9998 | 图 6、`analyze_addresses.py` |
| 往返与净额 | 45.4% 的金额在同一区块内原路返回；最大净流入 1,500.00 万、最大净流出 1,783.72 万美元，两者合计仅占毛额 0.09% | 图 6 |
| 链上核验 | 块 52,650,046 的 tx `0x0afdd3e0…` 在同一笔交易内借出并归还 238,890,119.82 USDC；该块 93 条日志与本地样本逐条一致 | `data/address_evidence.json` |

## 5. 可复现性

```bash
python fetch_data.py                 # 抓 DefiLlama 日度数据（免 key）
python make_figure.py                # 图 1
python -u fetch_transfers.py         # 24 小时采样（约 60 MB、3 分钟）
python -u make_transfer_figure.py    # 图 2
python -u analyze_roundtrips.py      # 镜像往返统计
python -u fetch_transfers_week.py    # 一周基线（约 440 MB、20–30 分钟）
python -u make_week_figure.py        # 图 3
python fetch_composition.py          # 抓各资产日度序列
python -u make_composition_figure.py # 图 5
python -u make_bridge_figure.py      # 图 4（只读已有 CSV）
python -u analyze_addresses.py       # 图 6 数据（读一周样本）
python -u make_address_figure.py     # 图 6
python -u make_cover.py              # 封面
```

依赖：Python 3、requests/pandas/matplotlib。提交记录与每个阶段的取舍写在仓库的决策记录里（本地文件 `00-web3副业与读博路线-决策记录.md`，未随仓库发布）。

## 6. 方法与限制（必须先说清楚的部分）

- **采样口径**：转账分析不是全量扫描。Base 约 2 秒一个块，一天约 43,200 块；一周全量需要数十 GB 流量。做法是每小时抽 1 个窗口、每窗口 50 个连续区块（约 100 秒），一周共 168 窗口 / 8,400 块，占该周区块数的 2.78%，且每天固定落在同一个分钟偏移上。
- **口径来源**：稳定币存量是 DefiLlama 的 `peggedUSD` 聚合口径，未做链上逐笔核对；份额分母只含被标记为锚定美元的资产。
- **已知缺口**：`minted` 字段在 2024-04-18 与 2024-04-20 缺失，会把整条流通量误记为桥入（图 4 右下角专门展示了这个陷阱）；除该案例外，涉及桥的统计都剔除这两天并按月度取月末值。
- **集中度指标的边界**：图 2/图 3 的集中度按「笔」排序，不按地址排序；同一比例在两个样本里对应的绝对笔数相差数倍，因此文中写成区间（前 1% 承担约 80%–93% 的金额）。
- **地址归属**：41 个大额地址只描述了行为，没有做标签库对照，不断言链下身份。
