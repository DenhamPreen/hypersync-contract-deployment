# HyperSync contract deployment finder

Give it a contract address. It finds the transaction that deployed the contract, who sent it and when, and saves the contract's bytecode, all with [Envio HyperSync](https://docs.envio.dev/docs/HyperSync/overview).

## Run it

You need Python 3 and a HyperSync API token from the [Envio Dashboard](https://envio.dev/app/api-tokens). The script has no other dependencies.

```bash
export ENVIO_API_TOKEN=your-token
python script.py                                   # Uniswap V3 Factory on Ethereum
python script.py <address> [chain]                 # any contract, chain is the HyperSync subdomain (eth, base, arbitrum...)
```

It takes a few seconds to about ten, because it searches the chain from block 0.

## What it prints

```
Contract            0x1f98431c8ad98523631ae4a59f267346ea31f984 on eth
Deployment tx       0x1e20cd6d47d7021ae7e437792823517eeadd835df09dde17ab45afd7a5df4603
Block               12,369,621  (2021-05-04 19:27:00 UTC)
Sent by             0x6c9fc64a53c1b71fb3f9af64d1ae3a4931a5f4e9
Init code           24939 bytes  0x60a060405234801561001057600080fd5b503060...
Runtime bytecode    24535 bytes  0x608060405234801561001057600080fd5b506004...
Saved               0x1f98431c8ad98523631ae4a59f267346ea31f984.bytecode.hex
Saved               0x1f98431c8ad98523631ae4a59f267346ea31f984.initcode.hex
```

## How it works

- **Init code and runtime bytecode are different things.** The init code is what the deployer sent, and it runs once. The runtime bytecode is what that run left on chain, and it is what you'd compare against verified source.
- **Traces find the deployment.** The script asks the chain's trace endpoint (`eth-traces.hypersync.xyz`) for the `create` trace whose `address` is your contract. The trace has the init code, the runtime bytecode and the transaction hash. Traces also see contracts that another contract deployed, such as factory clones. For those the script also prints "Created by" next to the wallet that sent the transaction.
- **Transactions give the details.** It then reads that block's transactions to find the deployment transaction's sender, and the block's timestamp.
- **Chains without traces** fall back to a plain transactions query on the `contract_address` field. That finds contracts a wallet deployed directly, and the init code is the transaction input. It can't see factory deployments, and HyperSync has no runtime bytecode there, so the script tells you to call `eth_getCode` on an RPC. Traces are only checked on Ethereum so far.

## Ask your coding agent

Paste this into Claude Code, Cursor or any coding agent:

```
Use Envio HyperSync (https://docs.envio.dev/docs/HyperSync/overview) to find the transaction that
deployed the contract 0x1F98431c8aD98523631AE4a59f267346ea31F984 on Ethereum, and its runtime bytecode.
My API token is in the ENVIO_API_TOKEN environment variable. Use the eth-traces.hypersync.xyz endpoint to
find the create trace for that address, then print the deployment transaction hash, block, timestamp and
sender, and save the bytecode to a file.
```
