# Base 链上 USDC：规模、份额与转账活动

作品集前两张图。数据全部来自免费的公开接口：DefiLlama Stablecoins API（免 key）与 Base 公共 RPC（免 key），脚本可复现。配套技术文：[中文 `article.md`](article.md) · [English `article.en.md`](article.en.md)。

| 图 | 看什么 | 数据源 |
| --- | --- | --- |
| 图 1 | 存量：Base 上 USDC 的规模、构成与份额（2023-08 – 2026-10 日度） | `stablecoins.llama.fi` |
| 图 2 | 流量：24 小时采样窗口内的转账笔数、金额分布与集中度 | Base RPC `eth_getLogs` |

---

## 图 1 · 流通量与市场份额

![Base USDC 流通量与份额](figures/base_usdc.png)

- **规模**：Base 上的 USDC 流通量从 2023-08-16 的 0.53 亿美元升到 2026-10-15 的 43.8 亿美元（约 83 倍）；峰值 47.7 亿美元（2026-01-22），此后回落约 8%。
- **结构**：2023-12-20 Circle 在 Base 上开始原生铸造之前，链上 USDC 全部靠跨链桥入；现在 43.72 亿美元是原生铸造，桥入只剩 632 万美元（0.14%）。
- **份额**：USDC 占 Base 上锚定美元的稳定币流通量的 84.4%（2026-10-15），高点为 97%（2024-04-23）。份额下滑不是 USDC 变少，而是分母里长出了别的美元稳定币。
- **当期构成**（2026-10-15 抓取）：USDC 43.89 亿、USDe 3.87 亿（7.5%）、rwaUSDi 1.47 亿、OUSD 0.90 亿、cgUSD 0.76 亿。

口径：

| 项 | 说明 |
| --- | --- |
| 端点 | `/stablecoins?chain=Base`（当期快照）、`/stablecoin/2`（USDC 分链历史）、`/stablecoincharts/Base`（Base 全链历史） |
| 频率 | 日度，UTC 零点；本图覆盖 2023-08-16 – 2026-10-15，共 1157 个点 |
| 流通量 | `circulating = minted − unreleased + bridgedTo`；图中把 `minted − unreleased` 记为「原生铸造」、其余记为「跨链桥入」，两段相加严格等于 `circulating`（脚本内有断言自检） |
| 份额 | USDC 在 Base 的流通量 ÷ Base 上所有 `peggedUSD` 稳定币的流通总量 |

---

## 图 2 · 转账活动（24 小时采样）

![Base USDC 转账活动](figures/base_usdc_transfers.png)

**采样口径**：以 2026-10-15 12:48Z（北京 20:48）链头为锚，往前每小时抽 1 个窗口、每窗口 50 个连续区块（1.63 分钟），共 24 窗口 / 1200 区块 / 93,656 条 Transfer 日志，占这 24 小时区块数的 2.8%。区间为 2026-10-14 12:48Z – 10-15 12:48Z。

- **笔数**：实测区间 1,710 – 3,616 笔/分钟，均值 2,387 笔/分钟。最低在北京时间 10-15 03:48，最高在 10-14 21:48。
- **金额分布**：中位数 100 美元、P90 5,498 美元、P99 263,797 美元、最大单笔 2.36 亿美元——跨度 6 个数量级。另有 1,310 笔金额为 0（同一批次里的尘埃/测试转账不做清理，单独报数）。
- **小额长尾**：17,200 笔不足 1 美元，占全部转账的 18.4%。用中位数描述 USDC 的转账毫无意义，长尾才是主体。
- **集中度**：按金额降序，前 0.1% 的转账占 87.7% 的金额，前 1% 占 92.6%，前 10% 占 99.6%。
- **地址**：13,159 个发送地址 / 12,158 个接收地址；最大的一个发送地址占 4.7% 的转账笔数，前 10 名发送方里有 6 个同时出现在头部接收方名单——做市/路由的往返特征。
- **铸造与销毁**：93,390 笔为普通转账，另有 mint 130 笔（合计 286 万美元）与 burn 136 笔（合计 181 万美元）。作者按同一窗口口径对比：采样窗口内原生增发的金额只占转账金额（70.5 亿美元）的 0.04%。

### 这张图是怎么拿到的

`eth_getLogs` 有单次结果上限：实测请求 100 个区块会被拒（`query exceeds max results 20000`），50 个区块返回约 1.2 万条日志。免费端点的真实瓶颈是带宽（约 0.4 MB/s）而不是速率限制，跑完 24 个窗口约 60 MB、200 秒。

免费端点会累积限流：`base-rpc.publicnode.com` 在累计约 200 MB 查询量后开始稳定返回 `HTTP 403`，退避重试无效。脚本因此改为**端点池轮换 + 被拒端点冷却 90 秒**，24 个窗口最终由 `base.drpc.org` 单点完成。

---

## 文件

```
fetch_data.py                 图 1：抓 DefiLlama 三个端点 → data/*.json + data/*.csv
make_figure.py                图 1：读 CSV 出图 → figures/base_usdc.{png,svg,pdf}
fetch_transfers.py            图 2：采样 eth_getLogs，可断点续跑（已存在的窗口跳过）
                              抓取阶段 → data/windows/plan.json + data/windows/wNN.json
                              汇总阶段 → data/transfers_windows.csv / transfers_sample.csv / transfers_summary.json
make_transfer_figure.py       图 2：读上述产物出图 → figures/base_usdc_transfers.{png,svg,pdf}
probe_rpc_list.py             一次性调查：逐个试公共端点，记录可用性与单窗口条数
probe_transfers.py            一次性调查：测 eth_getLogs 的区块上限与带宽
data/usdc_base_daily.csv      USDC 在 Base 的逐日流通量（拆原生铸造 / 跨链桥入）
data/base_stablecoins_daily.csv  Base 全链稳定币逐日流通量（份额分母）
data/base_stablecoins_now.csv    Base 各稳定币当期流通量
data/transfers_windows.csv    逐窗口统计（24 行，含笔数/金额分位/独立地址数/最大发送方占比）
data/transfers_sample.csv     逐笔转账（93,656 行：时间戳、区块、from、to、金额、类型）
data/windows/plan.json        采样锚点（链头 52,639,572、参考块、块速），随仓库提供
data/windows/wNN.json         每个窗口的原始日志（约 13 MB，未纳入版本库，重跑 fetch_transfers.py 即重建）
```

仓库里包含出图与文章直接读取的全部数据（含 `transfers_sample.csv`，93,656 行逐笔记录），不包含两类抓取中间产物：`data/raw_*.json` 与 `data/windows/w*.json`——它们体积大、内容与上表重复，跑一遍抓取脚本即可重新获得。

复现：

```bash
python fetch_data.py
python make_figure.py
python -u fetch_transfers.py          # 需要约 60 MB 出网带宽、200 秒
python -u make_transfer_figure.py
```

依赖：Python 3 + pandas + matplotlib（本机 Python 3.14.4 / matplotlib 3.11.1 / pandas 3.0.5 实测通过）。两个抓取脚本只用标准库，不需要任何 API key。

## 已知限制

- DefiLlama 是第三方聚合口径，未做链上逐笔核对；图 1 的数字只能算「该 API 的口径」。
- 图 1 里 `minted`、`unreleased` 两个字段 2023-12-20 起才有；此前按「全部为跨链桥入」处理，与该日 `circulating == bridgedTo` 的事实一致。份额分母只含 DefiLlama 标记为锚定美元的资产，不含 EUR/ARS 等其他锚定币。
- 图 2 是 2.8% 的区块抽样，且窗口是连续的 50 块，只能代表被抽中的时段；没有做日内分层加权，也没有按小时区分工作日与周末。
- 图 2 的地址数按字面去重，未区分 EOA 与合约、未做同一实体的归并；「前 N% 的转账占多少金额」是按笔排序，不是按地址排序。
- 图 2 的金额按 USDC 计价、1e6 精度还原，未做二次校验；mint/burn 只反映 Circle 的原生发行与回收，跨链桥入的 USDC 在链上表现为普通转账。
