"""从 DefiLlama 公开 API 拉取 Base 链上稳定币数据（免 key，2026-10-15 实测可用）。

三个端点：
  1) /stablecoins?chain=Base   —— Base 上每个稳定币资产的当前流通量（快照）
  2) /stablecoin/2             —— USDC（稳定币 id = 2）在各链的历史；取其中 Base 一条
  3) /stablecoincharts/Base    —— Base 全链稳定币流通量历史（做占比要用它当分母）

产物：
  data/raw_*.json             原始响应，便于回溯与复核
  data/usdc_base_daily.csv    USDC 在 Base 的逐日流通量（拆出原生铸造 / 跨链桥入）
  data/base_stablecoins_daily.csv  Base 全链稳定币逐日流通量
  data/base_stablecoins_now.csv    Base 上各稳定币当期流通量（做构成图用）
  data/meta.json              抓取时间与来源 URL

用法：python fetch_data.py
"""

import csv
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

API = "https://stablecoins.llama.fi"
ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data"
USDC_ID = 2  # DefiLlama peggedAssets 里 USDC 的 id，实测确认

SOURCE_URLS = {
    "stablecoins_base": f"{API}/stablecoins?chain=Base",
    "usdc_asset": f"{API}/stablecoin/{USDC_ID}",
    "base_chain_chart": f"{API}/stablecoincharts/Base",
}


def fetch(path: str) -> dict:
    with urllib.request.urlopen(f"{API}{path}", timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def day(epoch: int) -> str:
    """DefiLlama 的时间戳是 UTC 零点。"""
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d")


def pick(d: dict, *keys):
    """逐层取字段，缺字段返回 None——历史早期数据字段不全（如 minted 是后加的）。"""
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def write_csv(path: pathlib.Path, header: list, rows: list) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    raw = {}
    for name, url in SOURCE_URLS.items():
        raw[name] = fetch(url.split(".fi", 1)[1])
        (DATA / f"raw_{name}.json").write_text(
            json.dumps(raw[name], ensure_ascii=False), encoding="utf-8"
        )
        print(f"fetched {name}")

    # 1) USDC 在 Base 的逐日流通量
    tokens = raw["usdc_asset"]["chainBalances"]["Base"]["tokens"]
    write_csv(
        DATA / "usdc_base_daily.csv",
        ["date", "circulating_usd", "minted_usd", "unreleased_usd", "bridged_in_usd"],
        [
            [
                day(t["date"]),
                pick(t, "circulating", "peggedUSD"),
                pick(t, "minted", "peggedUSD"),
                pick(t, "unreleased", "peggedUSD"),
                pick(t, "bridgedTo", "peggedUSD"),
            ]
            for t in tokens
        ],
    )

    # 2) Base 全链稳定币逐日流通量（分母）
    chart = raw["base_chain_chart"]
    write_csv(
        DATA / "base_stablecoins_daily.csv",
        ["date", "total_circulating_usd", "total_unreleased_usd", "total_minted_usd"],
        [
            [
                day(int(c["date"])),
                pick(c, "totalCirculating", "peggedUSD"),
                pick(c, "totalUnreleased", "peggedUSD"),
                pick(c, "totalMintedUSD", "peggedUSD"),
            ]
            for c in chart
        ],
    )

    # 3) Base 上各稳定币的当期流通量（构成图用）
    assets = raw["stablecoins_base"]["peggedAssets"]
    rows = []
    for a in assets:
        usd = pick(a, "chainCirculating", "Base", "current", "peggedUSD")
        if usd:
            rows.append([a.get("symbol"), a.get("name"), a.get("id"), usd])
    rows.sort(key=lambda r: -r[3])
    write_csv(DATA / "base_stablecoins_now.csv", ["symbol", "name", "id", "circulating_usd"], rows)

    (DATA / "meta.json").write_text(
        json.dumps(
            {
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "fetched_at_utc8": datetime.now(timezone.utc)
                .astimezone()
                .isoformat(timespec="seconds"),
                "sources": SOURCE_URLS,
                "usdc_base_points": len(tokens),
                "base_chart_points": len(chart),
                "base_assets_with_usd": len(rows),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("wrote data/*.csv and data/meta.json")


if __name__ == "__main__":
    main()
