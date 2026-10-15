"""探针：在若干免 key 的 Base RPC 里找还能跑 eth_getLogs 的端点。"""

import json
import time
import urllib.error
import urllib.request

ENDPOINTS = [
    "https://base.publicnode.com",
    "https://base.drpc.org",
    "https://1rpc.io/base",
    "https://base.meowrpc.com",
    "https://base.blockpi.network/v1/rpc/public",
    "https://gateway.tenderly.co/public/base",
    "https://base-mainnet.public.blastapi.io",
    "https://base.llamarpc.com",
    "https://mainnet.base.org",
    "https://base.api.onfinality.io/public",
    "https://base.rpc.thirdweb.com",
]

USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def rpc(url, method, params, timeout=25):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "User-Agent": "web3-study/0.1"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw), time.time() - t0, len(raw)


for url in ENDPOINTS:
    try:
        msg, dt, n = rpc(url, "eth_blockNumber", [])
    except Exception as exc:  # noqa: BLE001
        print(f"{url:<48} 头块失败  {type(exc).__name__}: {str(exc)[:60]}")
        continue
    if "result" not in msg:
        print(f"{url:<48} 头块报错  {str(msg.get('error'))[:60]}")
        continue
    head = int(msg["result"], 16)
    try:
        msg, dt, n = rpc(
            url,
            "eth_getLogs",
            [{"fromBlock": hex(head - 9), "toBlock": hex(head), "address": USDC, "topics": [TOPIC]}],
        )
    except Exception as exc:  # noqa: BLE001
        print(f"{url:<48} 头块 OK({head})  getLogs 失败  {type(exc).__name__}: {str(exc)[:50]}")
        continue
    if "result" in msg:
        print(f"{url:<48} 头块 {head}  getLogs 10 块 = {len(msg['result'])} 条  {dt:.1f}s  {n/1024:.0f}KB")
    else:
        print(f"{url:<48} 头块 {head}  getLogs 报错  {str(msg.get('error'))[:70]}")
    time.sleep(1.0)
