# 发布素材 · 先用英文发一条 Base 分析（发布后 1–2 周再申请 Creator Grant）

面向公开渠道的投放素材。**串（第 1 节）**用于 X / Farcaster，**长文（第 2 节）**用于 Medium / Substack / paragraph / Reddit，**中文短版（第 3 节）**备用。
每条英文都已按 280 字符限长写过，可直接复制粘贴。

## 0. 发布前清单（2026-10-16 已全部执行，X 与 Farcaster 均已发布）

- [x] 附件图：首条挂封面 `figures/base_usdc_cover.png`，第 2–5 条挂对应单图（存量 / 构成 / 转账 / 一周基线）；两个平台都按这个方案挂了图
- [x] 链接：https://github.com/sbbbx/base-usdc （首条文字带 "Repo ↓"，末条给完整 URL 生成链接卡）
- [x] 可 @ 的对象：X 末条 `@base` `@buildonbase` `@DefiLlama`（均已解析为真账号）；Farcaster 发到 `base` 频道（首帖头部渲染出 `/base` 频道链接，已核验）
- [x] 不写：钱包地址、邮箱、KYC 信息、居住地 —— 逐条检查通过
- [x] 署名：`sbbbx`（仓库 handle 与 Farcaster `@sbbbx` 一致；X 账号为 `@bxs1524649`）
- [x] **X 串已发布**：首帖 https://x.com/bxs1524649/status/2110956429452742870
- [x] **Farcaster 串已发布**：首帖 https://farcaster.xyz/sbbbx/0x541bbfeb （`/base` 频道，7 条 + 5 图）
- 发布记录：`E:\PythonProjects\Web3\00-web3副业与读博路线-决策记录.md` §33（X，含 6 条 status id 与踩坑）与 §34（Farcaster，含 6 条 cast hash 与踩坑）

## 1. X / Farcaster 串（7 条）

**1/**
USDC on Base, measured from free public endpoints only. Five figures: $4.38B of stock, 84.4% share, a 24-hour block sample of every transfer, a one-week baseline, and the bridge channel's exit. Repo + bilingual write-up ↓

**2/**
Stock: $52.8M → $4.38B in 3.5 years, peak $4.77B. And 99.86% of it is now minted natively — the bridge channel is down to $6.3M from a $124M peak, a 94.9% retreat.

**3/**
Share: 84.4% of Base's dollar stablecoins, down from a 97.2% high. Not because USDC shrank — the denominator grew. USDe, rwaUSDi, OUSD, cgUSD and others arrived one by one, each with its own arrival date.

**4/**
Flow: 93,656 Transfer logs sampled over 24h. 2,387 transfers per minute, median size $96, and the top 1% of transfers carrying 92.6% of the value.

**5/**
A one-week baseline (730,778 logs, 168 hourly windows, 2.78% of that week's blocks) barely moves the median — $93 — but moves concentration to 80.5%. That metric is decided by a handful of whale transfers, so it belongs in a range, not a point.

**6/**
Of the 1,120 transfers ≥$1M in that week, every single one pairs with a same-second, equal-amount transfer going the other way, from 41 distinct addresses. The largest USDC flows on Base are round trips, not settlement.

**7/**
Method: keyless RPC only, one 50-block window per hour (2.8% of blocks), exact caveats printed in every figure. Code, data and the sampling recipe: github.com/sbbbx/base-usdc (MIT)

## 2. 长文（英文，约 650 词；Medium / Substack / Reddit 用）

**Title: USDC on Base, measured from free endpoints only**

I wanted to know what actually moves USDC on Base, using nothing that requires an API key, a subscription, or a paid plan. Two free sources were enough: DefiLlama's stablecoin API for daily stock and per-asset series, and public Base RPC endpoints for raw `Transfer` logs. Everything below is reproducible from the repo, and every figure states its own sampling method on the canvas.

**Stock and share.** USDC on Base went from $52.8M on 2023-08-16 to $4.38B on 2026-10-15, peaking at $4.77B on 2026-01-22. Almost all of that growth is native issuance: 99.86% of the stock is minted by Circle directly, and the bridge channel has retreated to $6.3M from its $124M peak in September 2023 — a 94.9% decline, with net outflows in 26 of the last 38 months. USDC's share of Base's dollar stablecoins is 84.4%, down from a 97.2% high in April 2024. The decline is not USDC shrinking: the denominator grew, as USDe, rwaUSDi, OUSD, cgUSD and others arrived one by one. Each arrival shows up as a step in the share series.

**Flow.** A full week of Base blocks is tens of gigabytes of logs, so I sampled: one 50-block window per hour (about 100 seconds each), 168 windows, 8,400 blocks — 2.78% of that week's blocks. That gives 730,778 Transfer logs for USDC. The median transfer is $93, and the distribution is heavy: 18% of transfers are under a dollar, while the largest single transfer is $238.9M. Concentration is the part that does not survive a change of sample. On a single day, the top 1% of transfers carried 92.6% of the value; on the week baseline, the same metric reads 80.5%, because it is decided by a handful of very large transfers. The robust statistics (median, the shape of the size distribution, the intraday rhythm — low around 06:00, peak around 21:00 local time) barely move.

**The flows are round trips.** The most interesting finding came from asking what the largest transfers actually do. Of the 1,120 transfers of $1M or more in the week sample — 71.0% of all value moved — every single one pairs with a same-second, equal-amount transfer in the opposite direction, from 41 distinct addresses. One address alone accounts for $12.7B of the sampled volume. Large USDC flows on Base are mostly net-zero round trips between a small set of addresses, not settlement between distinct users. That does not make the volume fake — routing and market-making are real activity — but it does mean per-transfer concentration is a poor proxy for genuine economic dispersion.

**Caveats, stated plainly.** Stablecoin stock is DefiLlama's aggregate figure, not verified transfer-by-transfer on chain. The `minted` field has two missing days (2024-04-18, 2024-04-20) which fabricate a $2.1B "bridge inflow" if you take the naive difference; those days are dropped. Concentration is measured per transfer, not per address. And the sampling window is 2.8% of blocks, fixed at the same minute offset each hour, so short-lived spikes outside those windows are invisible.

**Reproduce it.** Five figures, six scripts, MIT licensed: https://github.com/sbbbx/base-usdc. Bilingual write-up included. If you want the exact sampling recipe, it is in the README and repeated inside every figure.

## 3. 中文短版（约 300 字，备用）

只用免 key 的公开接口，我把 Base 上 USDC 的存量、份额、转账活动与跨链桥通道做成了五张图。存量三年半从 0.53 亿美元涨到 43.8 亿美元，其中 99.86% 已经由 Circle 原生发行，跨链桥这条通道从 1.24 亿美元的峰值退到 632 万美元。份额 84.4%，比 2024 年 4 月的高点 97.2% 低 12.8 个百分点，原因不是 USDC 变小，而是分母里陆续长出了 USDe、rwaUSDi、OUSD、cgUSD 等资产。转账侧按每小时抽一个 50 区块窗口采样（占该周区块的 2.78%，共 730,778 条日志）：中位数 93 美元、日内节律稳定，但「前 1% 承担多少金额」这个指标会随样本漂移（单日 92.6%、一周 80.5%）——因为它由少数天量转账决定。更值得记的是：一周里 1,120 笔百万美元以上的转账，每一笔都能在同一秒找到等额反向的另一笔，来自 41 个地址，最大的一笔 2.39 亿美元当天原路返回。仓库：github.com/sbbbx/base-usdc

## 4. 发布后 1–2 周：申请 Base Creator Grant

- 表单入口：https://forms.gle/sZ5cBADdXLfbbe1R8 （官方页面 docs.base.org/get-started/creators）
- 官方原话：最高 $4,000，明确收 “Writers covering Base (deep dives, memes, analysis, threads)”，队列制（“next cohort”）
- 申请时能拿出的证据链：公开仓库（5 图 + 中英双文 + 可复现脚本）→ 公开发布帖（本节第 1/2 节内容）→ 发布后的互动数据
- 仍需注意（页面未注明，属未证实）：结算币种、是否要 KYC、是否对地区有限制；申请是队列制，不是悬赏，何时回复不确定
