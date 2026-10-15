"""探针：确认 publicnode RPC 的 eth_getLogs 时延与响应规模，用来定采样窗口大小。"""

import json
import time
import urllib.request

RPC = "https://base-rpc.publicnode.com"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def call(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(
        RPC,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "web3-study/0.1"},
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read()
    return json.loads(raw), time.time() - t0, len(raw)


msg, dt, n = call("eth_blockNumber", [])
head = int(msg["result"], 16)
print(f"head = {head}  ({dt:.2f}s, {n}B)")

for span in (10, 50, 100):
    msg, dt, n = call(
        "eth_getLogs",
        [{"fromBlock": hex(head - span + 1), "toBlock": hex(head), "address": USDC, "topics": [TOPIC]}],
    )
    res = msg.get("result")
    if res is None:
        print(f"span={span:>4}  ERROR {msg.get('error')}  ({dt:.2f}s, {n/1024:.0f}KB)")
    else:
        print(f"span={span:>4}  logs={len(res):>5}  ({dt:.2f}s, {n/1024:.0f}KB)  keys={sorted(res[0].keys())}")
