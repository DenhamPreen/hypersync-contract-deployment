# Given a contract address, find the transaction that deployed it and the contract's bytecode, with Envio HyperSync.
# Usage: python script.py [address] [chain]     (defaults: Uniswap V3 Factory on eth)
# Python 3 standard library only. Set ENVIO_API_TOKEN first.
import datetime
import json
import os
import sys
import urllib.request

ADDRESS = (sys.argv[1] if len(sys.argv) > 1 else "0x1F98431c8aD98523631AE4a59f267346ea31F984").lower()
CHAIN = sys.argv[2] if len(sys.argv) > 2 else "eth"  # the HyperSync subdomain, e.g. eth, polygon, base, arbitrum

TOKEN = os.environ.get("ENVIO_API_TOKEN")
if not TOKEN:
    sys.exit("Set ENVIO_API_TOKEN (get one at https://envio.dev/app/api-tokens)")


def query(host, body):
    """Run a HyperSync query and follow next_block until the whole chain has been searched."""
    results = []
    while True:
        req = urllib.request.Request("https://%s.hypersync.xyz/query" % host, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", "Authorization": "Bearer " + TOKEN})
        res = json.load(urllib.request.urlopen(req, timeout=300))
        results += res["data"]
        if res["next_block"] >= res["archive_height"] or ("to_block" in body and res["next_block"] >= body["to_block"]):
            return results
        body["from_block"] = res["next_block"]


def num(x):
    return int(x, 16) if isinstance(x, str) else x


# 1. The trace where the contract was created. It holds the init code (what the deployer sent)
#    and the runtime bytecode (what ended up on chain). Traces see factory (CREATE/CREATE2) deployments too.
create = None
try:
    for batch in query(CHAIN + "-traces", {
            "from_block": 0, "traces": [{"type": ["create"], "address": [ADDRESS]}],
            "field_selection": {"trace": ["from", "address", "init", "code", "block_number", "transaction_hash"]}}):
        for t in batch.get("traces") or []:
            create = t
except Exception as e:
    print("No trace data for %s (%s), falling back to transactions" % (CHAIN, e), file=sys.stderr)

# 2. The deployment transaction itself. Without traces this finds contracts deployed directly by a wallet
#    (the receipt's contract_address), and the init code is the transaction input.
tx = None
if create:
    block = num(create["block_number"])
    for batch in query(CHAIN, {"from_block": block, "to_block": block + 1, "transactions": [{}],
                               "field_selection": {"transaction": ["hash", "from", "to", "input", "block_number"],
                                                   "block": ["number", "timestamp"]}}):
        for t in batch.get("transactions") or []:
            if t["hash"] == create["transaction_hash"]:
                tx = t
else:
    for batch in query(CHAIN, {"from_block": 0, "transactions": [{"contract_address": [ADDRESS]}],
                               "field_selection": {"transaction": ["hash", "from", "to", "input", "block_number"],
                                                   "block": ["number", "timestamp"]}}):
        for t in batch.get("transactions") or []:
            tx = t
if not tx:
    sys.exit("No deployment found for %s on %s. Is it a contract on that chain?" % (ADDRESS, CHAIN))

block = num(tx["block_number"])
timestamp = None
for batch in query(CHAIN, {"from_block": block, "to_block": block + 1, "include_all_blocks": True,
                           "field_selection": {"block": ["number", "timestamp"]}}):
    for b in batch.get("blocks") or []:
        timestamp = num(b["timestamp"])

init_code = (create or {}).get("init") or tx["input"]
runtime = (create or {}).get("code")

print("Contract            %s on %s" % (ADDRESS, CHAIN))
print("Deployment tx       %s" % tx["hash"])
print("Block               %s  (%s UTC)" % (format(block, ","), datetime.datetime.utcfromtimestamp(timestamp)))
print("Sent by             %s" % tx["from"])
if create and create["from"] != tx["from"]:
    print("Created by          %s  (a contract, such as a factory)" % create["from"])
print("Init code           %d bytes  %s..." % ((len(init_code) - 2) // 2, init_code[:42]))
if runtime:
    print("Runtime bytecode    %d bytes  %s..." % ((len(runtime) - 2) // 2, runtime[:42]))
    open(ADDRESS + ".bytecode.hex", "w").write(runtime)
    print("Saved               %s.bytecode.hex" % ADDRESS)
else:
    print("Runtime bytecode    not in HyperSync for %s (no trace data). Ask an RPC: eth_getCode(%s)" % (CHAIN, ADDRESS))
open(ADDRESS + ".initcode.hex", "w").write(init_code)
print("Saved               %s.initcode.hex" % ADDRESS)
