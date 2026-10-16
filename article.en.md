# USDC on Base: $4.38 Billion of Stock, and a Week-Long Slice of Flow

*English version of [`article.md`](article.md). Numbers and definitions are identical in both.*

Base is Coinbase's Ethereum layer 2, and USDC is the main form of on-chain dollars there. Two questions shape the money on this chain: how much USDC is there and how did it get there, and how does that money move — in a day, and in the week around it.

This article answers both with two kinds of free interface: the DefiLlama stablecoin endpoints for daily stock, and the public Base RPC's `eth_getLogs` for transfer detail. Every number carries its source and definition, and the scripts in this repository reproduce them line by line.

## 1. Sources and definitions

| Source | Use | Measured 2026-10-15/16 |
| --- | --- | --- |
| `stablecoins.llama.fi/stablecoincharts/Base` | Daily circulating supply of all USD stablecoins on Base (share denominator) | no key needed, 1,158 daily records |
| `stablecoins.llama.fi/stablecoin/2` | USDC (asset id = 2) history by chain | no key needed, 1,157 daily records on Base |
| `stablecoins.llama.fi/stablecoins?chain=Base` | Current snapshot per stablecoin | no key needed, 57 assets with a USD peg |
| Public Base RPC (rotating across drpc / publicnode / 1rpc / Tenderly / BlastAPI / thirdweb) | USDC Transfer logs | no key needed; per-query result cap |

Both interfaces need no registration and no key. That is what sets the resolution this study can reach, and what it cannot.

**Stock definition**: `circulating = minted − unreleased + bridgedTo`. `minted − unreleased` is recorded as native mint, the rest as bridged in. Across 1,157 daily points, the two parts add back to `circulating` with a maximum error of 0.00e+00.

**Flow definition**: anchored at block 52,639,572 (2026-10-15 12:48Z), one window is drawn every hour going back, each covering 50 consecutive blocks (1.63 minutes): 24 windows / 1,200 blocks / 93,656 Transfer logs, 2.8% of the blocks in those 24 hours, spanning 2026-10-14 12:48Z to 10-15 12:48Z. Amounts are reconstructed from USDC's 6 decimals (`int(data,16)/1e6`); a `from` of the zero address counts as mint, a `to` of zero as burn, everything else as a plain transfer.

**Week definition**: the same ruler run for seven consecutive days — still one window per hour of 50 consecutive blocks — giving 168 windows / 8,400 blocks / 274 minutes, 2.778% of that week's blocks, spanning 2026-10-09 01:35Z to 10-16 02:04Z (fetched 2026-10-16). This run returned 730,778 logs over 441 MB of egress, 1,082 seconds of RPC time and zero server-side retries.

**Why 50-block windows**: `eth_getLogs` caps a single query at 20,000 results — a 100-block request is rejected in practice (`query exceeds max results 20000`), while 50 blocks return about 12,000 logs and leave margin. The real bottleneck on free endpoints is bandwidth (~0.4 MB/s) rather than rate limiting, and endpoints also throttle cumulatively: `base-rpc.publicnode.com` starts returning `HTTP 403` consistently after roughly 200 MB of query volume, and backoff retries do not help, so the script rotates through a pool of endpoints and cools down any that rejects it for 90 seconds.

## 2. Stock: 83× growth, and one structural replacement

![USDC supply and share on Base](figures/base_usdc.png)

As Figure 1 shows, USDC on Base grew from $53 million on 2023-08-16 to $4.38 billion on 2026-10-15, about 83×; the peak of $4.77 billion came on 2026-01-22, followed by an 8% decline.

The growth was not smooth. The first jump came in March–May 2024: the $500M mark fell on 3-22, $1B on 3-28, $2B on 4-17 and $3B on 5-27. The $4 billion mark had to wait until 2025-09-16. In monthly net terms, April 2024 brought $1.393 billion in, the largest single month on record; May 2026 took $290 million out, the largest outflow.

Structurally, one replacement happened. Before 2023-12-20, all USDC on Base arrived over bridges; that day Circle began native minting on Base, and the `minted` field only exists from that date. By 2026-10-15, $4.372 billion is natively minted and only $6.32 million is bridged in, or 0.14%.

Share is a separate story. USDC held 84.4% of USD-pegged stablecoin supply on Base on 2026-10-15, against a high of 97% (2024-04-23). The decline is not USDC shrinking — it kept growing over the same period — but the denominator growing new assets.

Those rivals arrived one after another. Figure 5 decomposes Base's USD stablecoin total by asset: cgUSD, EUSD and USDe appear in 2024-02, 2024-05 and 2024-08; MSUSD, rwaUSDi and OUSD in 2025-11, 2026-03 and 2026-09. Of the 12.8 points USDC gave up, USDe alone accounts for 7.4, and the two assets that only appeared in 2026 (rwaUSDi, OUSD) account for 4.6; the other six assets and the long tail split less than one point.

![Base USD stablecoin composition](figures/base_usdc_composition.png)

## 3. Flow: a 39-minute slice spanning six orders of magnitude

![USDC transfer activity on Base](figures/base_usdc_transfers.png)

As Figure 2 shows, the 24 windows total 39.1 minutes; of the 93,656 logs, 93,390 are plain transfers, 130 are mints and 136 are burns.

**Rate** ranged from 1,710 to 3,616 transfers per minute, averaging 2,387. The low came at 03:48 Beijing time on 10-15, the high at 21:48 on 10-14.

**Amount distribution** is what the figure is really about. The median is $100, P90 $5,498, P99 $263,797, and the largest single transfer $236 million: six orders of magnitude. Another 17,200 transfers are under $1 (18.4% of the total) and 1,310 are exactly zero. The mean or the median of USDC transfers says nothing useful.

**Concentration**: sorted by amount, the top 0.1% of transfers carry 87.7% of the value, the top 1% carry 92.6%, and the top 10% carry 99.6%. Addresses are just as concentrated: 13,159 senders and 12,158 receivers, with the largest sender accounting for 4.7% of all transfers, and six of the top ten senders also appearing among the top receivers. That is the signature of market makers and routers: the same addresses shuttling value. Those three percentages are the one-day definition; the next section corrects them with a week of data.

**Mints and burns are nearly invisible by value**: 130 mints totalling $2.86 million and 136 burns totalling $1.81 million, just 0.04% of the $7.05 billion transferred in the same windows.

## 4. A one-week baseline: the rhythm holds, the concentration is shuttling

![One-week sampling baseline for USDC on Base](figures/base_usdc_week.png)

Figure 3 runs the same ruler for seven days, and yields two stable readings and one correction.

**The rate rhythm holds.** Averaged over the seven days, the low is 1,903 transfers per minute at 06:00 Beijing time and the high is 3,841 at 21:00; each individual day oscillates around that rhythm, and none departs by an order of magnitude. Day-to-day variation is small too: daily averages fall between 2,196 and 3,219 transfers per minute, and the weekend (10-10, 10-11) is no lower than the weekdays.

**The shape of the amount distribution holds as well.** Over the week the median is $93, P90 $7,782, P99 $425,056 and the largest single transfer $239 million — almost coincident with Figure 2's single-day curve. What is stable is the tail-insensitive statistic; swap in an extreme-driven metric and the conclusion moves with the sample.

**Concentration is exactly such a metric.** Over the week the top 0.1% of transfers carry 69.9%, the top 1% carry 80.5% and the top 10% carry 99.4%, against 87.7% / 92.6% / 99.6% for Figure 2's single day. The gap is not market movement: fold the week down to the single day's top-1% count (923 transfers) and the top 1% carries only 70.4%. "Top 1%" is relative to sample size; the two samples differ about 7.8-fold in count, so the same percentage means eight times as many transfers. Such figures belong in a range, with the definition stated alongside.

**The correction comes from what the large transfers are.** In the week's sample, all 1,120 transfers of $1 million or more — $26.79 billion, 71.0% of the total amount — have a same-second, equal-amount, opposite-direction counterpart inside the sample; only 41 addresses take part, one of them sending out $12.72 billion (its off-chain identity was not verified here). The $239 million transfer in Figure 3 walked straight back in the same second. Most of the "flow" measured by value is shuttling between the same addresses with a net of zero: a value-weighted flow counts carriage as transfer.

## 5. The bridge channel's exit

![The bridge channel for USDC on Base](figures/base_usdc_bridge.png)

Bridged stock (circulating supply minus `minted − unreleased`, matching DefiLlama's `bridgedTo`) peaked at $124.3 million on 2023-09-04, fell in 26 of the following 38 months, and stood at $6.32 million on 2026-10-15, 94.9% below the peak; circulating supply grew by $4.325 billion over the same period, all of it native minting.

The figure also caught a definition trap: `minted` is still missing on 2024-04-18 and 2024-04-20, and on a missing day the whole $2.1 billion of supply is booked as bridged in while the real magnitude is $83 million. Any series split as "circulating = native + bridged" needs its components checked for completeness first. DefiLlama's bridge-detail endpoint returned HTTP 402 on 2026-10-16, so this section describes channel-level stock only and names no bridges.

## 6. Reading the five figures together

$4.38 billion of stock and $37.75 billion of transfers inside the week's sampled windows cannot be subtracted from each other: they do not measure the same thing.

Three takeaways:

1. Metrics like "USDC transfer count" are inflated by small transfers: 18.4% of them are under $1.
2. Value-side concentration and flow are both set by a handful of addresses shuttling back and forth: the top 1% carries roughly 80–93% of the value depending on the definition, and 71% of the million-dollar-plus part nets to zero. Separate carriage from transfer before reading flows.
3. Falling share and growing size can hold at the same time; the denominator decides the share. An analysis that plots one asset will reach the opposite conclusion.
4. Constituent channels can exit: bridge-in went from the only entry point to a 0.14% remainder while the growth was carried by native issuance. Read "where it came from" separately from "how much there is".

## 7. Limitations

- Figures 2 and 3 each rest on a 2.8% block sample in contiguous 50-block windows, so they represent only the periods drawn, with no intraday weighting; Figure 3's windows also sit at the same minute offset (:35 of every hour), and its intraday rhythm is a seven-day average, not any single day.
- Addresses are deduplicated literally: EOAs and contracts are not distinguished, and no entity-level merging was done. Concentration is ranked by transfer, not by address.
- Amounts are denominated in USDC and reconstructed from 6 decimals without a second check; mint and burn only reflect Circle's native issuance and redemption, while USDC arriving over a bridge appears on-chain as an ordinary transfer.
- Figure 1 rests on a third-party aggregation and was not reconciled trade by trade; the `minted` and `unreleased` fields only exist from 2023-12-20, and everything before that is treated as bridged in; the share denominator includes only assets DefiLlama flags as USD-pegged, excluding EUR and other pegs.
- Two self-checks from this work belong here as well. The histogram floor once silently dropped every transfer below it, and a new variable collided with the bar-position variable, so `log10(0)` raised `ValueError: Maximum allowed size exceeded`.
- The same-second, equal-amount, reverse-direction match is done inside the sample only: a counterpart falling outside the sampled windows is invisible, so 71.0% is a lower bound on this kind of shuttling.
- The 41 large addresses have no independent evidence of off-chain identity (no label provider was consulted); the text describes their behaviour only.
- Figure 4's bridged stock is DefiLlama's `bridgedTo` split (a third-party aggregation, not reconciled trade by trade); `minted` is missing on 2024-04-18 and 2024-04-20, when the whole supply would be booked as bridged in, so those days are dropped and the view is monthly; the bridge-detail endpoint returned HTTP 402 on 2026-10-16, so no individual bridge can be confirmed.
- Figure 5's arrival date is the day the asset first shows non-zero circulating supply in DefiLlama's data, which is not necessarily its launch date; smaller assets' history may be backfilled or revised upstream. Its "other" band is the residual against the total, contains assets that have since exited, and names none of them.

## 8. Reproducing

```bash
cd base-usdc
python fetch_data.py            # fetch three DefiLlama endpoints
python make_figure.py           # figure 1
python -u fetch_transfers.py    # sample Transfer logs, resumable per window, ~200 s / 60 MB
python -u make_transfer_figure.py   # figure 2
python -u fetch_transfers_week.py   # 7 days × 24 windows, ~20 min / 440 MB
python -u make_week_figure.py       # figure 3
python -u analyze_roundtrips.py     # mirror round-trip share (reads data/week/sample.csv)
python -u make_bridge_figure.py     # figure 4 (reads existing CSVs, no new fetch)
python -u fetch_composition.py      # figure 5 data: 12 requests
python -u make_composition_figure.py   # figure 5
```

Requires Python 3 with pandas and matplotlib; the two fetch scripts use only the standard library. Verified on Python 3.14.4 / matplotlib 3.11.1 / pandas 3.0.5.

All interfaces were measured on 2026-10-15 and 2026-10-16 (UTC+8). Figure 1 covers 2023-08-16 to 2026-10-15; Figure 2 covers 2026-10-14 12:48Z to 10-15 12:48Z; Figure 3 covers 2026-10-09 01:35Z to 10-16 02:04Z; Figures 4 and 5 cover 2023-08-16 to 2026-10-15 (same source as Figure 1).
